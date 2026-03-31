from typing import Any, List
from fastapi import APIRouter, Depends

from app.routers.deps import get_current_user
from app.models.user import UserInDB
from app.schemas.jobs import JobRecommendation
from app.core.logger import logger

router = APIRouter()

MOCK_JOBS = [
    { "id": 1, "title": "Frontend Developer Intern", "company": "TechCorp", "type": "Internship", "pay": "$40-50/hr", "duration": "12 weeks", "match_score": 92, "date_posted": "2 days ago" },
    { "id": 2, "title": "Full Stack Engineer", "company": "StartupX", "type": "Full-time", "pay": "$120k-150k", "duration": "Permanent", "match_score": 85, "date_posted": "Just now" },
    { "id": 3, "title": "React UI Developer", "company": "DesignStudio", "type": "Part-time", "pay": "$60/hr", "duration": "6 months", "match_score": 78, "date_posted": "1 week ago" },
    { "id": 4, "title": "Machine Learning Engineer", "company": "AI Labs", "type": "Full-time", "pay": "$150k-200k", "duration": "Permanent", "match_score": 60, "date_posted": "3 days ago" },
    { "id": 5, "title": "DevOps Intern", "company": "CloudBase", "type": "Internship", "pay": "$35/hr", "duration": "6 months", "match_score": 45, "date_posted": "1 month ago" },
]

@router.get("/recommendations", response_model=List[JobRecommendation])
def get_job_recommendations(
    current_user: UserInDB = Depends(get_current_user),
) -> Any:
    """
    Get job recommendations based on user skills.
    In a real application this would use AI/Matching algorithm.
    """
    logger.info(f"Generated job recommendations for {current_user.email}")
    return MOCK_JOBS

from typing import Optional

@router.get("/search", response_model=List[JobRecommendation])
def search_jobs(
    q: Optional[str] = None,
    type: Optional[str] = None,
    payMin: Optional[str] = None,
    duration: Optional[str] = None,
    datePosted: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user),
) -> Any:
    """
    Search jobs with query and filters.
    """
    logger.info(f"Searching jobs for {current_user.email} with query={q}")
    
    results = MOCK_JOBS
    if q:
        query = q.lower()
        results = [j for j in results if query in j["title"].lower() or query in j["company"].lower()]
    
    if type:
        t = type.lower()
        results = [j for j in results if t in j["type"].lower()]
        
    return results
