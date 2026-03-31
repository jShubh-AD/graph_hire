from pydantic import BaseModel
from typing import Optional

class JobRecommendation(BaseModel):
    id: Optional[int] = None
    title: str
    company: str
    type: str
    pay: str
    duration: Optional[str] = None
    match_score: Optional[int] = None
    date_posted: Optional[str] = None
