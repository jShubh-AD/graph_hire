from typing import List, Optional
from pydantic import BaseModel, Field
import uuid

class SkillLevel(BaseModel):
    skill: str
    proficiency: float

class UserInDB(BaseModel):
    userId: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    hashed_password: str
    bio: Optional[str] = None
    skills: List[SkillLevel] = Field(default_factory=list)
