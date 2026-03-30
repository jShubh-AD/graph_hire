from typing import Any, List
from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import get_current_user
from app.models.user import UserInDB
from app.schemas.resume import ParsedSkill
from app.core.logger import logger

router = APIRouter()

@router.post("/upload", response_model=List[ParsedSkill])
def upload_resume(
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_user),
) -> Any:
    """
    Mock endpoint to upload resume and return extracted skills.
    In a real app, this would use an LLM or parser to extract data from the file.
    """
    logger.info(f"Resume uploaded by {current_user.email}: {file.filename}")
    
    # Return mock data as requested
    return [
        {"skill": "python", "proficiency": 0.8},
        {"skill": "sql", "proficiency": 0.7},
        {"skill": "fastapi", "proficiency": 0.75}
    ]
