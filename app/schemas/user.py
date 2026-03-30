from typing import List, Optional
from pydantic import BaseModel, EmailStr

class SkillLevel(BaseModel):
    skill: str
    proficiency: float

# Shared properties
class UserBase(BaseModel):
    email: EmailStr
    name: str

# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

# Properties to receive via API on update (profile)
class UserUpdate(BaseModel):
    skills: List[SkillLevel]
    bio: Optional[str] = None

class UserResponse(UserBase):
    userId: str
    bio: Optional[str] = None
    skills: List[SkillLevel]

    class Config:
        from_attributes = True
