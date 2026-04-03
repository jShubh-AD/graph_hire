"""
Pydantic schemas for the Friends/Network feature.
"""
from typing import List, Optional
from pydantic import BaseModel


class FollowResponse(BaseModel):
    message: str


class CompanyInfo(BaseModel):
    company_id: Optional[str] = None
    company_name: Optional[str] = None
    role: Optional[str] = None


class FriendResponse(BaseModel):
    userId: str
    name: str
    email: str
    bio: Optional[str] = None
    current_company: Optional[CompanyInfo] = None
    skills: List[str] = []


class SuggestionResponse(BaseModel):
    userId: str
    name: str
    email: str
    shared_skill_count: int
    current_company: Optional[CompanyInfo] = None
    skills: List[str] = []


class ReferralContact(BaseModel):
    userId: str
    name: str
    email: str
    role: Optional[str] = None
    company_name: Optional[str] = None


class ReferralPathResponse(BaseModel):
    referrals: List[ReferralContact]
    message: Optional[str] = None
