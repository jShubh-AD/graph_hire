from typing import Any, List
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException

from app.routers.deps import get_current_user
from app.models.user import UserInDB
from app.schemas.resume import ParsedSkill
from app.services.ai_service import ai_service
from app.db.tigergraph import get_all_skills_list, upsert_edge
from app.core.logger import logger

router = APIRouter()

@router.post("/upload", response_model=List[ParsedSkill])
async def upload_resume(
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_user),
) -> Any:
    """
    Upload a resume (PDF), extract skills using AI, and map them to the user's profile.
    Only skills existing in our database will be extracted.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF resumes are supported.")

    logger.info(f"AI Extraction started for {current_user.get('email', 'Unknown')}: {file.filename}")
    
    try:
        # 1. Read PDF content
        content = await file.read()
        
        # 2. Get current database skill list for the AI to pick from
        db_skills = get_all_skills_list()
        
        # 3. Use AI to extract skills matched against DB skills
        extracted_skills = await ai_service.parse_resume_skills(content, db_skills)
        
        # 4. Save HAS_SKILL relationships to TigerGraph
        user_id = current_user["userId"]
        for skill in extracted_skills:
            try:
                upsert_edge(
                    from_type="User",
                    from_id=str(user_id),
                    edge_type="HAS_SKILL",
                    to_type="Skill",
                    to_id=str(skill.skillId),
                    attributes={"proficiency": float(skill.proficiency)}
                )
                logger.info(f"Mapped skill {skill.name} (ID: {skill.skillId}) to user {user_id}")
            except Exception as e:
                logger.error(f"Failed to save HAS_SKILL for {skill.name}: {e}")

        return extracted_skills

    except Exception as e:
        logger.error(f"Resume parsing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Error parsing resume: {str(e)}")
