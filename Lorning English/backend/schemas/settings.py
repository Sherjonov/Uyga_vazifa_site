from typing import Optional

from pydantic import BaseModel, Field


class TeacherSettingsIn(BaseModel):
    absence_penalty: float = Field(ge=0, le=1000)
    late_penalty: float = Field(default=3, ge=0, le=1000)
    hw_late_penalty: float = Field(default=5, ge=0, le=1000)
    hw_missing_penalty: float = Field(default=5, ge=0, le=1000)
    ai_daily_limit: int = Field(default=8, ge=1, le=200)
    similarity_threshold: int = Field(default=70, ge=1, le=100)
    vocab_warning_limit: int = Field(default=2, ge=0, le=20)
    vocab_pass_percent: int = Field(default=60, ge=1, le=100)
    grid_max_score: float = Field(default=50, ge=1, le=100000)
    danger_missed_homework: int = Field(ge=1, le=100)
    danger_low_test_score: float = Field(ge=0, le=10)
    danger_absences: int = Field(ge=1, le=100)
    danger_score_drop: float = Field(ge=1, le=10000)
    danger_inactive_days: int = Field(ge=1, le=365)


class PasswordChangeIn(BaseModel):
    old_password: str = Field(min_length=1, max_length=72)
    new_password: str = Field(min_length=6, max_length=72)


class PreferencesIn(BaseModel):
    language: Optional[str] = Field(default=None, pattern=r"^(uz|en|ru)$")
    theme: Optional[str] = Field(default=None, pattern=r"^(light|dark)$")


class ProfileIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
