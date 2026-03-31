from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class SkillLevel(BaseModel):
    skill: str
    proficiency: float


class UserBase(BaseModel):
    email: str
    name: str


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserUpdate(BaseModel):
    skills: Optional[List[SkillLevel]] = None
    bio: Optional[str] = None


class UserResponse(BaseModel):
    userId: str
    email: str
    name: str
    bio: Optional[str] = None
    skills: List[SkillLevel] = []

    model_config = ConfigDict(from_attributes=True)
