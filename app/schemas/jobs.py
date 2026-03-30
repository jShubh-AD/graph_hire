from pydantic import BaseModel

class JobRecommendation(BaseModel):
    title: str
    company: str
    type: str
    pay: str
