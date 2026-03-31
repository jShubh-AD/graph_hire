from pydantic import BaseModel
from typing import Optional, List, Any


class JobResponse(BaseModel):
    jobId: str
    title: str
    description: Optional[str] = None
    company_name: Optional[str] = None
    job_type: Optional[str] = None
    pay_min: Optional[float] = None
    pay_max: Optional[float] = None
    duration: Optional[str] = None
    date_posted: Optional[str] = None
    score: Optional[float] = None


class QueryInfo(BaseModel):
    type: str
    gsql: str
    latency_ms: float


class RecommendedJobsResponse(BaseModel):
    jobs: List[JobResponse]
    query_info: QueryInfo


# Keep backward-compatible alias for older code paths
class JobRecommendation(BaseModel):
    id: Optional[str] = None
    title: str
    company: Optional[str] = None
    type: Optional[str] = None
    pay: Optional[str] = None
    duration: Optional[str] = None
    match_score: Optional[float] = None
    date_posted: Optional[str] = None
