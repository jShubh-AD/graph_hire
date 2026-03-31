from typing import Any
from fastapi import APIRouter, Depends

from app.routers.deps import get_current_user
from app.models.user import UserInDB
from app.schemas.user import UserResponse, UserUpdate
from app.core.logger import logger

router = APIRouter()

@router.post("/profile", response_model=UserResponse)
def update_profile(
    user_in: UserUpdate,
    current_user: UserInDB = Depends(get_current_user),
) -> Any:
    """
    Update profile details for the current user including skills and proficiency.
    """
    if user_in.bio is not None:
        current_user.bio = user_in.bio
    
    if user_in.skills is not None:
        # Pydantic validates input format, simply store it
        current_user.skills = user_in.skills

    logger.info(f"User {current_user.email} updated profile. Skills: {len(current_user.skills)}")
    return current_user

@router.get("/profile", response_model=UserResponse)
def get_profile(
    current_user: UserInDB = Depends(get_current_user),
) -> Any:
    """
    Get profile details for the current user including skills and proficiency.
    """
    return current_user
