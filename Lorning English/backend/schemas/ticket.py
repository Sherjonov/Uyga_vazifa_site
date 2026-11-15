from typing import Optional

from pydantic import BaseModel, Field


class TicketIn(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=5, max_length=5000)


class TicketAdminIn(BaseModel):
    status: Optional[str] = Field(default=None, pattern=r"^(new|in_progress|resolved)$")
    admin_reply: Optional[str] = Field(default=None, max_length=5000)
