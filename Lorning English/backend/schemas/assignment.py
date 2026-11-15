from typing import Optional

from pydantic import BaseModel, Field


class ReviewIn(BaseModel):
    score: Optional[float] = None
    comment: Optional[str] = Field(default=None, max_length=2000)
    analysis_confirmed: bool = False
