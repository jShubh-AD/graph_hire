from fastapi import APIRouter, HTTPException, Depends
from typing import List
from pydantic import BaseModel
from app.db.tigergraph import get_all_skills_list

router = APIRouter(tags=["Skills"])

class SkillResponse(BaseModel):
    id: int
    name: str


@router.get("", response_model=List[SkillResponse])
async def get_all_skills():
    """
    Returns all skills in the database for frontend dropdowns.
    """
    try:
        return get_all_skills_list()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
