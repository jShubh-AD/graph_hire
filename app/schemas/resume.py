from pydantic import BaseModel

class ParsedSkill(BaseModel):
    skill: str
    proficiency: float
