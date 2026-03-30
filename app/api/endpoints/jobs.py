from typing import Any, List
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import UserInDB
from app.schemas.jobs import JobRecommendation
from app.core.logger import logger

router = APIRouter()

@router.get("/recommendations", response_model=List[JobRecommendation])
def get_job_recommendations(
    current_user: UserInDB = Depends(get_current_user),
) -> Any:
    """
    Get job recommendations based on user skills.
    In a real application this would use AI/Matching algorithm.
    """
    logger.info(f"Generated job recommendations for {current_user.email}")
    
    # Return dummy recommendation data as requested
    return [
        {
            "title": "Backend Intern",
            "company": "ABC",
            "type": "intern",
            "pay": "20k"
        }
    ]
