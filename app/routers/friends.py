"""
Friends/Network router for GraphHire.

POST   /friends/follow/{target_user_id}    — Follow a user
DELETE /friends/unfollow/{target_user_id}  — Unfollow a user
GET    /friends/following                  — List users you follow
GET    /friends/suggestions                — Suggested connections
GET    /jobs/{job_id}/referral-path        — Friends at the hiring company
"""
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status

from app.routers.deps import get_current_user
from app.db.tigergraph import get_tg_connection, upsert_edge, run_installed_query
from app.schemas.friends import (
    FollowResponse,
    FriendResponse,
    CompanyInfo,
    SuggestionResponse,
    ReferralContact,
    ReferralPathResponse,
)
from app.core.logger import logger

# Router for /friends/* endpoints
router = APIRouter()

# Separate router for the /jobs/{job_id}/referral-path endpoint
# This gets mounted under /jobs prefix in main.py
jobs_router = APIRouter()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _parse_company(attrs: dict) -> CompanyInfo | None:
    """Extract current company from GSQL accumulator attributes."""
    cid = attrs.get("current_company_id", "")
    cname = attrs.get("current_company_name", "")
    role = attrs.get("current_role", "")
    if cid or cname:
        return CompanyInfo(company_id=cid or None, company_name=cname or None, role=role or None)
    return None


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/follow/{target_user_id}", response_model=FollowResponse)
def follow_user(
    target_user_id: str,
    current_user: dict = Depends(get_current_user),
) -> Any:
    """Create a FOLLOWS edge from the current user to the target user."""
    user_id = current_user["userId"]

    if user_id == target_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot follow yourself.",
        )

    # Verify target user exists
    conn = get_tg_connection()
    try:
        target = conn.getVertices("User", where=f'userId=="{target_user_id}"', limit=1)
        if not target:
            raise HTTPException(status_code=404, detail="User not found.")
        target_name = target[0].get("attributes", {}).get("name", target_user_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching target user {target_user_id}: {e}")
        raise HTTPException(status_code=500, detail="Could not verify target user.")

    # Upsert FOLLOWS edge
    try:
        upsert_edge("User", user_id, "FOLLOWS", "User", target_user_id)
        logger.info(f"User {user_id} now follows {target_user_id}")
        return {"message": f"Following {target_name}"}
    except Exception as e:
        logger.error(f"Failed to create FOLLOWS edge {user_id} -> {target_user_id}: {e}")
        raise HTTPException(status_code=500, detail="Could not follow user.")


@router.delete("/unfollow/{target_user_id}", response_model=FollowResponse)
def unfollow_user(
    target_user_id: str,
    current_user: dict = Depends(get_current_user),
) -> Any:
    """Delete the FOLLOWS edge from the current user to the target user."""
    user_id = current_user["userId"]

    if user_id == target_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot unfollow yourself.",
        )

    try:
        from app.db.tigergraph import tg_delete, _G
        tg_delete(f"/graph/{_G()}/edges/User/{user_id}/FOLLOWS/User/{target_user_id}")
        logger.info(f"User {user_id} unfollowed {target_user_id}")
        return {"message": "Unfollowed"}
    except Exception as e:
        logger.error(f"Failed to delete FOLLOWS edge {user_id} -> {target_user_id}: {e}")
        raise HTTPException(status_code=500, detail="Could not unfollow user.")


@router.get("/following", response_model=List[FriendResponse])
def get_following(
    current_user: dict = Depends(get_current_user),
) -> Any:
    """Return all users the current user follows, with their current company."""
    user_id = current_user["userId"]

    try:
        res = run_installed_query("get_following", {"p_userId": user_id})
    except Exception as e:
        logger.error(f"get_following query failed for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch following list.")

    friends: List[FriendResponse] = []
    for item in res:
        for f in item.get("friends", []):
            attrs = f.get("attributes", {})
            friends.append(
                FriendResponse(
                    userId=attrs.get("userId", f.get("v_id", "")),
                    name=attrs.get("name", ""),
                    email=attrs.get("email", ""),
                    bio=attrs.get("bio"),
                    current_company=_parse_company(attrs),
                    skills=attrs.get("skills", []),
                )
            )
    return friends


@router.get("/suggestions", response_model=List[SuggestionResponse])
def get_suggestions(
    current_user: dict = Depends(get_current_user),
) -> Any:
    """Return top 10 suggested connections based on shared skills."""
    user_id = current_user["userId"]

    try:
        res = run_installed_query("suggest_connections", {"p_userId": user_id})
    except Exception as e:
        logger.error(f"suggest_connections query failed for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Could not fetch suggestions.")

    suggestions: List[SuggestionResponse] = []
    for item in res:
        for c in item.get("candidates", []):
            attrs = c.get("attributes", {})
            suggestions.append(
                SuggestionResponse(
                    userId=attrs.get("userId", c.get("v_id", "")),
                    name=attrs.get("name", ""),
                    email=attrs.get("email", ""),
                    shared_skill_count=int(attrs.get("shared_skill_count", 0)),
                    current_company=_parse_company(attrs),
                    skills=attrs.get("skills", []),
                )
            )
    return suggestions


# ─── Jobs sub-router ──────────────────────────────────────────────────────────

@jobs_router.get("/{job_id}/referral-path", response_model=ReferralPathResponse)
def get_referral_path(
    job_id: str,
    current_user: dict = Depends(get_current_user),
) -> Any:
    """Return connections who work at the company that posted the given job."""
    user_id = current_user["userId"]

    try:
        res = run_installed_query("get_referral_path", {"p_userId": user_id, "p_jobId": job_id})
    except Exception as e:
        logger.error(f"get_referral_path query failed (user={user_id}, job={job_id}): {e}")
        raise HTTPException(status_code=500, detail="Could not fetch referral path.")

    referrals: List[ReferralContact] = []
    for item in res:
        for r in item.get("referrals", []):
            attrs = r.get("attributes", {})
            referrals.append(
                ReferralContact(
                    userId=attrs.get("userId", r.get("v_id", "")),
                    name=attrs.get("name", ""),
                    email=attrs.get("email", ""),
                    role=attrs.get("role"),
                    company_name=attrs.get("company_name"),
                )
            )

    if not referrals:
        return ReferralPathResponse(
            referrals=[],
            message="No connections at this company yet",
        )

    return ReferralPathResponse(referrals=referrals)
