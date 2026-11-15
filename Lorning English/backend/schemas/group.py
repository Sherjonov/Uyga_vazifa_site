from pydantic import BaseModel, Field


class GroupIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    kind: str = Field(default="english", pattern=r"^(english|school|university|circle)$")


class GroupRename(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class MemberIn(BaseModel):
    student_id: int
