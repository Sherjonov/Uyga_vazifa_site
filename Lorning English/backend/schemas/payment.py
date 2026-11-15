from typing import Optional

from pydantic import BaseModel, Field


class PaymentReviewIn(BaseModel):
    action: str = Field(pattern=r"^(approve|reject|fraud)$")
    note: Optional[str] = Field(default=None, max_length=500)
