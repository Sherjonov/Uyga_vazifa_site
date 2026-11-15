from typing import Optional

from pydantic import BaseModel, Field

from models.user import User
from utils import iso


class OTPRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=255)


class OTPVerify(BaseModel):
    identifier: str = Field(min_length=3, max_length=255)
    code: str = Field(pattern=r"^\d{6}$")


class RegisterComplete(BaseModel):
    registration_token: str
    name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=6, max_length=72)


class StudentRegister(BaseModel):
    group_id: int  # 1-qadam: o'qituvchi yaratgan guruh
    name: str = Field(min_length=2, max_length=120)  # 2-qadam: ism-familiya
    password: str = Field(min_length=6, max_length=72)
    registration_token: Optional[str] = None  # REQUIRE_OTP=true bo'lsa (kod tasdiqlangach olinadi)
    identifier: Optional[str] = Field(default=None, max_length=255)  # REQUIRE_OTP=false bo'lsa email/telefon


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=72)


class OnboardingIn(BaseModel):
    track: str = Field(default="english", pattern=r"^(english|school|university|circle)$")
    role: str = Field(pattern=r"^(student|teacher)$")


def user_out(u: User) -> dict:
    return {
        "id": u.id, "name": u.name, "email": u.email, "phone": u.phone, "role": u.role, "track": u.track,
        "language": u.language, "theme": u.theme, "total_score": round(u.total_score or 0, 2),
        "onboarded": u.onboarded, "is_active": u.is_active, "created_at": iso(u.created_at),
    }
