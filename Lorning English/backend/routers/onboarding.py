from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from deps import get_db, get_current_user
from messages import AppError
from models.user import User
from schemas.auth import OnboardingIn, user_out

router = APIRouter(prefix="/onboarding", tags=["onboarding"])

# Platforma faqat ingliz tili uchun: yagona yo'nalish "english" (o'quvchi / o'qituvchi)
TRACK_ROLES = {
    "english": ["student", "teacher"],
    "school": ["student", "teacher"],      # eski qiymatlar bilan moslik
    "university": ["student", "teacher"],
    "circle": ["student", "teacher"],
}


@router.get("/options")
def options():
    return {"tracks": TRACK_ROLES}


@router.post("")
def complete_onboarding(data: OnboardingIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.onboarded:
        raise AppError(409, "already_onboarded")
    if data.role not in TRACK_ROLES.get(data.track, []):
        raise AppError(400, "invalid_role_for_track")
    user.track = "english"
    user.role = data.role
    user.onboarded = True
    db.commit()
    return user_out(user)
