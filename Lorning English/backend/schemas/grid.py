from pydantic import BaseModel, Field


class ColumnIn(BaseModel):
    title: str = Field(min_length=1, max_length=80)


class CellIn(BaseModel):
    column_id: int
    student_id: int
    value: str = Field(default="", max_length=40)
