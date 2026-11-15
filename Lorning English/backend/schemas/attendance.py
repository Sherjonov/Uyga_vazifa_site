from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class AttendanceIn(BaseModel):
    group_id: int
    student_id: int
    date: date
    status: Optional[str] = Field(default=None, pattern=r"^(present|absent|excused|late)$")
    lesson_title: Optional[str] = Field(default=None, max_length=120)


class AttendanceBulkIn(BaseModel):
    group_id: int
    date: date
    status: str = Field(pattern=r"^(present|absent|excused|late)$")
