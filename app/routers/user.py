"""
User router — profile update with TigerGraph HAS_SKILL edges.
POST /profile   → upsert Skill vertices + HAS_SKILL edges for current user
GET  /profile   → return current user's attributes
"""
import uuid
from typing import Any

from fastapi import APIRouter, Depends

from app.routers.deps import get_current_user
from app.db.tigergraph import get_tg_connection
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
    if user_in.skills:
        for sk in user_in.skills:
            skill_name = sk.skill.strip().lower()
            skill_id = f"skill_user_{skill_name.replace(' ', '_')}"

            # Upsert skill vertex
            conn.upsertVertex(
                "Skill",
                skill_id,
                attributes={"skillId": skill_id, "name": sk.skill, "category": "user_defined"},
            )

            # Upsert HAS_SKILL edge
            conn.upsertEdge("User", user_id, "HAS_SKILL", "Skill", skill_id,
                            attributes={"proficiency": sk.proficiency})
            skill_list.append({"skill": sk.skill, "proficiency": sk.proficiency})

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
    """Fetch current user's profile + skills from TigerGraph."""
    user_id = current_user["userId"]
    conn = get_tg_connection()

    # Fetch HAS_SKILL edges to get the user's skills
    skill_list = []
    try:
        edges = conn.getEdges("User", user_id, "HAS_SKILL")
        for edge in edges:
            target_id = edge.get("to_id", "")
            proficiency = edge.get("attributes", {}).get("proficiency", 0.0)
            # Fetch skill name
            sk_result = conn.getVerticesById("Skill", [target_id])
            if sk_result:
                name = sk_result[0]["attributes"].get("name", target_id)
            else:
                name = target_id
            skill_list.append({"skill": name, "proficiency": proficiency})
    except Exception as e:
        logger.warning(f"Could not fetch skills for user {user_id}: {e}")

    return {
        "userId": user_id,
        "name": current_user.get("name", ""),
        "email": current_user.get("email", ""),
        "bio": current_user.get("bio", ""),
        "skills": skill_list,
    }
