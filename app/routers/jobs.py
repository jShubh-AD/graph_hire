"""
Jobs router — all endpoints backed by TigerGraph GSQL queries.

GET  /jobs/recommended  → skill_match + similar_users_jobs, merged + deduped
GET  /jobs/search       → filtered GSQL query
POST /jobs/save         → upsert SAVED edge
"""
import time
from datetime import datetime, timezone
from typing import Any, List, Optional
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException

from app.routers.deps import get_current_user
from app.db.tigergraph import get_tg_connection
from app.schemas.jobs import JobResponse, RecommendedJobsResponse, QueryInfo, PaginationInfo
from app.schemas.user import SkillLevel
from app.core.logger import logger

router = APIRouter()

_SKILL_MATCH_GSQL = (
    "SELECT j FROM User:u -(HAS_SKILL)-> Skill:s -(REQUIRES_SKILL_REVERSE)-> JobPost:j "
    "ACCUM j.@score += proficiency * importance ORDER BY @score DESC LIMIT 20"
)

_SIMILAR_USERS_GSQL = (
    "SELECT j FROM User:u -(HAS_SKILL)-> Skill:s -(HAS_SKILL_REVERSE)-> User:u2 "
    "-(APPLIED_TO)-> JobPost:j WHERE u2 != u ACCUM j.@score += 1 ORDER BY @score DESC LIMIT 20"
)


def _row_to_job(row: dict) -> JobResponse:
    """Convert a TigerGraph vertex result dict to a JobResponse."""
    attrs = row.get("attributes", row)
    date_val = attrs.get("date_posted", "")
    if hasattr(date_val, "isoformat"):
        date_str = date_val.isoformat()
    else:
        date_str = str(date_val) if date_val else ""

    return JobResponse(
        jobId=attrs.get("jobId", row.get("v_id", "")),
        title=attrs.get("title", ""),
        description=attrs.get("description", ""),
        company_name=attrs.get("company_name", ""),
        job_type=attrs.get("job_type", ""),
        pay_min=attrs.get("pay_min"),
        pay_max=attrs.get("pay_max"),
        duration=attrs.get("duration", ""),
        date_posted=date_str,
        score=attrs.get("@score", attrs.get("score")),
        status=attrs.get("status", "Open"),
        is_flagged=attrs.get("is_flagged", False),
        flag_count=attrs.get("flag_count", 0),
        skills=[],  # Populated later by _fetch_skills_for_jobs
    )


def _fetch_skills_for_jobs(conn: Any, jobs: List[JobResponse]):
    """
    Parallelized fetch to attach required skills to a list of jobs.
    Uses ThreadPoolExecutor to make N concurrent head requests.
    """
    if not jobs:
        return

    job_to_skill_refs = {}  # jobId -> list of (skillId, importance)
    all_skill_ids = set()

    def fetch_job_edges(job: JobResponse):
        try:
            edges = conn.getEdges("JobPost", job.jobId, "REQUIRES_SKILL")
            refs = []
            for e in edges:
                skill_id = e.get("to_id")
                importance = e.get("attributes", {}).get("importance", 1.0)
                refs.append((skill_id, importance))
            return job.jobId, refs
        except Exception as e:
            logger.warning(f"Failed to fetch edges for job {job.jobId}: {e}")
            return job.jobId, []

    # 1. Fetch all REQUIRES_SKILL edges in parallel
    max_workers = min(10, len(jobs)) if jobs else 1
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(fetch_job_edges, jobs))

    for job_id, refs in results:
        job_to_skill_refs[job_id] = refs
        for sid, _ in refs:
            all_skill_ids.add(sid)

    if not all_skill_ids:
        return

    # 2. Batch fetch all Skill vertices (single call)
    try:
        skill_vertices = conn.getVerticesById("Skill", list(all_skill_ids))
        # Ensure we use int keys for consistent lookup
        skill_names = {int(v["v_id"]): v.get("attributes", {}).get("name", v["v_id"]) for v in skill_vertices}
    except Exception as e:
        logger.warning(f"Batch skill lookup failed: {e}")
        skill_names = {int(sid): sid for sid in all_skill_ids}

    # 3. Attach SkillLevel objects
    for job in jobs:
        refs = job_to_skill_refs.get(job.jobId, [])
        job.skills = [
            SkillLevel(skill_id=int(sid), skill_name=skill_names.get(int(sid), ""), proficiency=imp)
            for sid, imp in refs
        ]


@router.get("/recommendations", response_model=RecommendedJobsResponse)
def get_job_recommendations(
    page: int = 1,
    limit: int = 10,
    current_user: dict = Depends(get_current_user),
) -> Any:
    """
    Run the optimized hybrid recommendation GSQL query (skill match + collaborative filtering).
    Returns paged results with pre-fetched skill metadata in a single REST call.
    """
    user_id = current_user["userId"]
    conn = get_tg_connection()

    start = time.monotonic()
    
    try:
        # Run the all-in-one optimized query
        params = {
            "p_userId": user_id,
            "p_page": page,
            "p_limit": limit
        }
        res = conn.runInstalledQuery("recommend_jobs_optimized", params)
        
        if not res or not isinstance(res, list):
            logger.warning(f"No result from recommend_jobs_optimized for {user_id}")
            return RecommendedJobsResponse(
                jobs=[],
                pagination=PaginationInfo(
                    total_items=0, total_pages=0, page=page, limit=limit, has_next=False, has_prev=False
                ),
                query_info=QueryInfo(type="optimized-hybrid", gsql="recommend_jobs_optimized", latency_ms=0)
            )

        # TigerGraph returns a list of result sets (one for each PRINT statement)
        # res[0] is {"jobs": [...]}
        # res[1] is {"total_count": N}
        raw_jobs = []
        total_items = 0
        
        for item in res:
            if "jobs" in item:
                raw_jobs = item["jobs"]
            if "total_count" in item:
                total_items = item["total_count"]

        jobs = []
        for row in raw_jobs:
            # row format from GSQL PagedJobs[...]:
            # { "v_id": ..., "attributes": { "jobId": ..., "skills": [{"skill": "python", "proficiency": 1.0}, ...] } }
            job = _row_to_job(row)
            
            # Map skills from GSQL TUPLE format to our SkillLevel schema
            raw_skills = row.get("attributes", {}).get("skills", [])
            job.skills = [
                SkillLevel(
                    skill_id=int(s.get("skillId", 0)), 
                    skill_name=s.get("skillName", ""), 
                    proficiency=s.get("proficiency", 0.0)
                )
                for s in raw_skills
            ]
            jobs.append(job)

        latency_ms = round((time.monotonic() - start) * 1000, 1)
        total_pages = (total_items + limit - 1) // limit if limit > 0 else 1

        logger.info(f"Recommended {len(jobs)} jobs (total {total_items}) for user {user_id} in {latency_ms}ms")
        
        return RecommendedJobsResponse(
            jobs=jobs,
            pagination=PaginationInfo(
                total_items=total_items,
                total_pages=total_pages,
                page=page,
                limit=limit,
                has_next=page < total_pages,
                has_prev=page > 1
            ),
            query_info=QueryInfo(
                type="Optimized Hybrid (Skills + Collaborative)",
                gsql=f"recommend_jobs_optimized(userId='{user_id}', page={page}, limit={limit})",
                latency_ms=latency_ms,
            ),
        )

    except Exception as e:
        logger.error(f"Recommendation engine failed: {e}")
        # Return empty but valid response to avoid breaking UI
        return RecommendedJobsResponse(
            jobs=[],
            pagination=PaginationInfo(
                total_items=0, total_pages=0, page=page, limit=limit, has_next=False, has_prev=False
            ),
            query_info=QueryInfo(type="error", gsql="N/A", latency_ms=0)
        )


@router.get("/search", response_model=List[JobResponse])
def search_jobs(
    job_type: Optional[str] = None,
    pay_min: Optional[float] = None,
    duration: Optional[str] = None,
    status: str = "Open",
    include_flagged: bool = False,
    current_user: dict = Depends(get_current_user),
) -> Any:
    """
    Filter jobs directly from TigerGraph using attribute conditions.
    """
    conn = get_tg_connection()

    conditions = []
    if not include_flagged:
        conditions.append("is_flagged==false")
    if status:
        conditions.append(f'status=="{status}"')
    
    if job_type:
        conditions.append(f'job_type=="{job_type}"')
    if pay_min is not None:
        conditions.append(f"pay_min>={pay_min}")
    if duration:
        conditions.append(f'duration=="{duration}"')

    where_clause = " AND ".join(conditions) if conditions else None

    try:
        results = conn.getVertices("JobPost", where=where_clause, limit=50)
    except Exception as e:
        logger.error(f"Job search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Graph query failed: {e}")

    jobs = [_row_to_job(r) for r in results]
    _fetch_skills_for_jobs(conn, jobs)
    logger.info(f"Search returned {len(jobs)} jobs for user {current_user['userId']}")
    return jobs


@router.post("/report/{job_id}")
def report_job(
    job_id: str,
    reason: str,
    current_user: dict = Depends(get_current_user),
) -> Any:
    """Report a job and increment flag count. Auto-flag if threshold reached (3)."""
    user_id = current_user["userId"]
    conn = get_tg_connection()

    # 1. Create REPORTED edge
    reported_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn.upsertEdge(
            "User", user_id,
            "REPORTED",
            "JobPost", job_id,
            attributes={"reported_at": reported_at, "reason": reason},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit report: {e}")

    # 2. Increment flag_count on JobPost and check threshold
    try:
        res = conn.getVerticesById("JobPost", [job_id])
        if not res:
            raise HTTPException(status_code=404, detail="Job not found")
        
        attrs = res[0].get("attributes", {})
        current_count = attrs.get("flag_count", 0)
        new_count = current_count + 1
        is_flagged = new_count >= 3  # Auto-flag after 3 reports

        conn.upsertVertex(
            "JobPost", job_id,
            attributes={"flag_count": new_count, "is_flagged": is_flagged}
        )
        
        # 3. Check and flag company if needed
        if is_flagged:
            # Find the company that posted this job
            posted_by = conn.getEdges("JobPost", job_id, "POSTED_BY")
            if posted_by:
                company_id = posted_by[0]["to_id"]
                company_res = conn.getVerticesById("Company", [company_id])
                if company_res:
                    c_attrs = company_res[0].get("attributes", {})
                    c_flag_count = c_attrs.get("flag_count", 0) + 1
                    c_is_flagged = c_flag_count >= 2 # Flag company if 2+ of its jobs are flagged
                    conn.upsertVertex(
                        "Company", company_id,
                        attributes={"flag_count": c_flag_count, "is_flagged": c_is_flagged}
                    )
        
        return {
            "status": "reported",
            "job_id": job_id,
            "flag_count": new_count,
            "is_flagged": is_flagged
        }
    except Exception as e:
        logger.error(f"Error during flag threshold check: {e}")
        return {"status": "reported", "job_id": job_id, "note": "Report saved, but error updating counters"}


@router.get("/flagged", response_model=List[JobResponse])
def get_flagged_jobs(
    current_user: dict = Depends(get_current_user),
) -> Any:
    """Get all flagged jobs for review/admin purposes."""
    conn = get_tg_connection()
    try:
        # Fetch vertices where is_flagged is true
        results = conn.getVertices("JobPost", where="is_flagged==true", limit=100)
        jobs = [_row_to_job(r) for r in results]
        _fetch_skills_for_jobs(conn, jobs)
        return jobs
    except Exception as e:
        logger.error(f"Failed to fetch flagged jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save/{job_id}")
def save_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
) -> Any:
    """Upsert a SAVED edge between current User and a JobPost."""
    user_id = current_user["userId"]
    conn = get_tg_connection()

    # Verify job exists
    try:
        job = conn.getVerticesById("JobPost", [job_id])
        if not job:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    saved_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn.upsertEdge(
            "User", user_id,
            "SAVED",
            "JobPost", job_id,
            attributes={"saved_at": saved_at},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save job: {e}")

    logger.info(f"User {user_id} saved job {job_id}")
    return {"status": "saved", "job_id": job_id, "saved_at": saved_at}


@router.post("/apply/{job_id}")
def apply_to_job(
    job_id: str,
    current_user: dict = Depends(get_current_user),
) -> Any:
    """Upsert an APPLIED_TO edge between current User and a JobPost."""
    user_id = current_user["userId"]
    conn = get_tg_connection()

    # Verify job exists
    try:
        job = conn.getVerticesById("JobPost", [job_id])
        if not job:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    applied_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn.upsertEdge(
            "User", user_id,
            "APPLIED_TO",
            "JobPost", job_id,
            attributes={"applied_at": applied_at},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply to job: {e}")

    logger.info(f"User {user_id} applied to job {job_id}")
    return {"status": "applied", "job_id": job_id, "applied_at": applied_at}


@router.get("/saved", response_model=List[JobResponse])
def get_saved_jobs(
    current_user: dict = Depends(get_current_user),
) -> Any:
    """Get all jobs saved by the current user."""
    user_id = current_user["userId"]
    conn = get_tg_connection()
    try:
        # Fetch JobPost vertices connected via SAVED edge
        results = conn.getNeighbors("User", user_id, edgeType="SAVED", targetVertexType="JobPost")
        jobs = [_row_to_job(r) for r in results]
        _fetch_skills_for_jobs(conn, jobs)
        return jobs
    except Exception as e:
        logger.error(f"Failed to fetch saved jobs for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/applied", response_model=List[JobResponse])
def get_applied_jobs(
    current_user: dict = Depends(get_current_user),
) -> Any:
    """Get all jobs the current user has applied to."""
    user_id = current_user["userId"]
    conn = get_tg_connection()
    try:
        results = conn.getNeighbors("User", user_id, edgeType="APPLIED_TO", targetVertexType="JobPost")
        jobs = [_row_to_job(r) for r in results]
        _fetch_skills_for_jobs(conn, jobs)
        return jobs
    except Exception as e:
        logger.error(f"Failed to fetch applied jobs for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reported", response_model=List[JobResponse])
def get_reported_jobs(
    current_user: dict = Depends(get_current_user),
) -> Any:
    """Get all jobs the current user has reported."""
    user_id = current_user["userId"]
    conn = get_tg_connection()
    try:
        results = conn.getNeighbors("User", user_id, edgeType="REPORTED", targetVertexType="JobPost")
        jobs = [_row_to_job(r) for r in results]
        _fetch_skills_for_jobs(conn, jobs)
        return jobs
    except Exception as e:
        logger.error(f"Failed to fetch reported jobs for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

