"""
Jobs router — all endpoints backed by TigerGraph GSQL queries.

GET  /jobs/recommended  → skill_match + similar_users_jobs, merged + deduped
GET  /jobs/search       → filtered GSQL query
POST /jobs/save         → upsert SAVED edge
"""
import time
from datetime import datetime, timezone
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException

from app.routers.deps import get_current_user
from app.db.tigergraph import get_tg_connection
from app.schemas.jobs import JobResponse, RecommendedJobsResponse, QueryInfo
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
    )


@router.get("/recommended", response_model=RecommendedJobsResponse)
def get_job_recommendations(
    current_user: dict = Depends(get_current_user),
) -> Any:
    """
    Run skill_match and similar_users_jobs GSQL queries, merge + dedupe results,
    and return them with query_info metadata.
    """
    user_id = current_user["userId"]
    conn = get_tg_connection()

    start = time.monotonic()
    jobs_by_id: dict[str, JobResponse] = {}

    # --- skill_match ---
    try:
        result1 = conn.runInstalledQuery("skill_match", {"p_userId": user_id})
        if result1 and isinstance(result1, list):
            for item in result1:
                job_list = item.get("jobs", [])
                for row in job_list:
                    job = _row_to_job(row)
                    if job.jobId not in jobs_by_id or (job.score or 0) > (jobs_by_id[job.jobId].score or 0):
                        jobs_by_id[job.jobId] = job
    except Exception as e:
        logger.warning(f"skill_match failed for {user_id}: {e}")

    # --- similar_users_jobs ---
    try:
        result2 = conn.runInstalledQuery("similar_users_jobs", {"p_userId": user_id})
        if result2 and isinstance(result2, list):
            for item in result2:
                job_list = item.get("jobs", [])
                for row in job_list:
                    job = _row_to_job(row)
                    if job.jobId not in jobs_by_id:
                        jobs_by_id[job.jobId] = job
    except Exception as e:
        logger.warning(f"similar_users_jobs failed for {user_id}: {e}")

    # Fallback: if both queries returned nothing (user has no skills yet), return top jobs
    if not jobs_by_id:
        try:
            fallback = conn.getVertices("JobPost", limit=20)
            for row in fallback:
                job = _row_to_job(row)
                jobs_by_id[job.jobId] = job
        except Exception as e:
            logger.error(f"Fallback job fetch failed: {e}")

    latency_ms = round((time.monotonic() - start) * 1000, 1)

    sorted_jobs = sorted(jobs_by_id.values(), key=lambda j: j.score or 0, reverse=True)

    logger.info(f"Recommended {len(sorted_jobs)} jobs for user {user_id} in {latency_ms}ms")
    return RecommendedJobsResponse(
        jobs=sorted_jobs,
        query_info=QueryInfo(
            type="2-hop skill traversal + collaborative filtering",
            gsql=f"skill_match(userId='{user_id}') + similar_users_jobs(userId='{user_id}')",
            latency_ms=latency_ms,
        ),
    )


@router.get("/search", response_model=List[JobResponse])
def search_jobs(
    job_type: Optional[str] = None,
    pay_min: Optional[float] = None,
    duration: Optional[str] = None,
    date_posted: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
) -> Any:
    """
    Filter jobs directly from TigerGraph using attribute conditions.
    """
    conn = get_tg_connection()

    conditions = []
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
    logger.info(f"Search returned {len(jobs)} jobs for user {current_user['userId']}")
    return jobs


@router.post("/save")
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
