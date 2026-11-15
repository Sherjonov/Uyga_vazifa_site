from typing import Optional

from pydantic import BaseModel, Field


class DirectIn(BaseModel):
    recipient_id: int
    body: str = Field(min_length=1, max_length=4000)


class ParentContactIn(BaseModel):
    parent_name: Optional[str] = Field(default=None, max_length=120)
    phone: Optional[str] = Field(default=None, max_length=32)
    email: Optional[str] = Field(default=None, max_length=255)


class ParentSendIn(BaseModel):
    student_id: int
    body: str = Field(min_length=1, max_length=1500)
    channel: str = Field(default="auto", pattern=r"^(auto|sms|email|telegram)$")
    # Tanlangan ota-ona (botga ulangan). Berilsa xabar faqat shu ota-onaning Telegram profiliga boradi.
    parent_link_id: Optional[int] = None
