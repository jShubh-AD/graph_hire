from pydantic import BaseModel

class ParsedSkill(BaseModel):
    skillId: int
    name: str # skill name
    proficiency: float
