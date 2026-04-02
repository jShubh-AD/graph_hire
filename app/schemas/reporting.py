from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ReportJobRequest(BaseModel):
    reason: str
    description: Optional[str] = None
