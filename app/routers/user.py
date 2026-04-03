"""
User router — profile update with TigerGraph HAS_SKILL edges.
POST /profile   → upsert Skill vertices + HAS_SKILL edges for current user
GET  /profile   → return current user's attributes
"""
import uuid
from typing import Any

from fastapi import APIRouter, Depends

from app.routers.deps import get_current_user
from app.db.tigergraph import get_tg_connection, ensure_skill_exists, get_skill_by_id
from app.schemas.user import UserResponse, UserUpdate
from app.core.logger import logger

router = APIRouter()


@router.post("/profile", response_model=UserResponse)
def update_profile(
    user_in: UserUpdate,
    current_user: dict = Depends(get_current_user),
) -> Any:
    """
    Upsert Skill vertices and HAS_SKILL edges for the authenticated user.
    """
    user_id = current_user["userId"]
    conn = get_tg_connection()

    if user_in.bio is not None:
        conn.upsertVertex("User", user_id, attributes={"bio": user_in.bio})

    skill_list = []
    if user_in.skills is not None:
        # 1. Clear existing skills for replacement logic
        try:
            conn.deleteEdges("User", user_id, "HAS_SKILL")
            logger.info(f"Cleared existing skills for user {user_id} before update")
        except Exception as e:
            logger.error(f"Failed to clear skills for user {user_id}: {e}")

        # 2. Add new skills
        for sk in user_in.skills:
            # Shift from name-based to ID-based lookup
            skill_info = get_skill_by_id(sk.skill_id)

            if not skill_info:
                logger.warning(f"User {user_id} tried to add unknown skill ID: {sk.skill_id}. Skipping.")
                continue

            # Upsert HAS_SKILL edge
            conn.upsertEdge("User", user_id, "HAS_SKILL", "Skill", str(sk.skill_id),
                            attributes={"proficiency": sk.proficiency})
            
            skill_list.append({
                "skill_id": sk.skill_id,
                "skill_name": skill_info["name"],
                "proficiency": sk.proficiency
            })

    logger.info(f"User {current_user['email']} updated profile with {len(skill_list)} skills")
    return {
        "userId": user_id,
        "name": current_user.get("name", ""),
        "email": current_user.get("email", ""),
        "bio": user_in.bio or current_user.get("bio", ""),
        "skills": skill_list,
    }


@router.get("/profile", response_model=UserResponse)
def get_profile(
    current_user: dict = Depends(get_current_user),
) -> Any:
    """Fetch current user's profile + skills from TigerGraph using installed query."""
    user_id = current_user["userId"]
    conn = get_tg_connection()

    try:
        res = conn.runInstalledQuery("get_user_profile", {"p_userId": user_id})
        
        if res and isinstance(res, list):
            for item in res:
                if "seed" in item and len(item["seed"]) > 0:
                    user_data = item["seed"][0].get("attributes", {})
                    
                    # Convert skills from Tuples
                    raw_skills = user_data.get("skills", [])
                    
                    skill_dict = {}
                    for s in raw_skills:
                        name = s.get("skillName", "")
                        prof = s.get("proficiency", 0.0)
                        sid = s.get("skillId", 0)
                        
                        # Deduplicate by name, keeping highest proficiency if duplicate
                        if name not in skill_dict or prof > skill_dict[name]["proficiency"]:
                            skill_dict[name] = {
                                "skill_id": int(sid),
                                "skill_name": name,
                                "proficiency": prof
                            }
                    
                    return {
                        "userId": user_data.get("userId", user_id),
                        "name": user_data.get("name", current_user.get("name", "")),
                        "email": user_data.get("email", current_user.get("email", "")),
                        "bio": user_data.get("bio", current_user.get("bio", "")),
                        "skills": list(skill_dict.values()),
                    }
    except Exception as e:
        logger.error(f"Failed to fetch profile via get_user_profile: {e}")

    # Fallback if DB error
    return {
        "userId": user_id,
        "name": current_user.get("name", ""),
        "email": current_user.get("email", ""),
        "bio": current_user.get("bio", ""),
        "skills": [],
    }
