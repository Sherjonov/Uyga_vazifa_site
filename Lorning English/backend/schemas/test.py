from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class QuestionIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    options: List[str] = Field(min_length=2, max_length=6)
    correct_index: int = Field(ge=0)
    explanation: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("options")
    @classmethod
    def clean_options(cls, v):
        v = [o.strip() for o in v]
        if any(not o for o in v):
            raise ValueError("empty option")
        return v

    @model_validator(mode="after")
    def check_correct(self):
        if self.correct_index >= len(self.options):
            raise ValueError("correct_index out of range")
        return self


class TestGenerateIn(BaseModel):
    topic: str = Field(min_length=2, max_length=200)
    count: int = Field(default=20, ge=1, le=50)
    options_count: int = Field(default=4, ge=2, le=6)
    model: Optional[str] = None


class TestReplaceIn(BaseModel):
    topic: str = Field(min_length=2, max_length=200)
    options_count: int = Field(default=4, ge=2, le=6)
    avoid: List[str] = Field(default_factory=list, max_length=60)
    model: Optional[str] = None


class TestCreate(BaseModel):
    group_id: int
    title: str = Field(min_length=1, max_length=200)
    duration_minutes: int = Field(ge=1, le=300)
    questions: List[QuestionIn] = Field(min_length=1, max_length=300)
    is_published: bool = False


class TestUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    duration_minutes: Optional[int] = Field(default=None, ge=1, le=300)
    is_published: Optional[bool] = None
    questions: Optional[List[QuestionIn]] = Field(default=None, min_length=1, max_length=300)


class AnswersIn(BaseModel):
    answers: Dict[str, int] = Field(default_factory=dict)


class RetakeIn(BaseModel):
    test_id: int
    reason: str = Field(min_length=5, max_length=500)
