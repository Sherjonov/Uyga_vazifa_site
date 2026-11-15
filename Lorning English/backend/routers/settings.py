from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from deps import get_db, get_current_user, require_role
from messages import AppError
from models.user import User
from schemas.auth import user_out
from schemas.settings import TeacherSettingsIn, PasswordChangeIn, PreferencesIn, ProfileIn
from security import hash_password, verify_password
from services import scoring

router = APIRouter(prefix="/settings", tags=["settings"])


def _s_out(s) -> dict:
    return {
        "absence_penalty": s.absence_penalty, "late_penalty": s.late_penalty, "hw_late_penalty": s.hw_late_penalty,
        "hw_missing_penalty": s.hw_missing_penalty, "ai_daily_limit": s.ai_daily_limit,
        "similarity_threshold": s.similarity_threshold, "vocab_warning_limit": s.vocab_warning_limit,
        "vocab_pass_percent": s.vocab_pass_percent, "grid_max_score": s.grid_max_score, "danger_missed_homework": s.danger_missed_homework,
        "danger_low_test_score": s.danger_low_test_score, "danger_absences": s.danger_absences,
        "danger_score_drop": s.danger_score_drop, "danger_inactive_days": s.danger_inactive_days,
    }


@router.get("/teacher")
def get_teacher_settings(db: Session = Depends(get_db), user: User = Depends(require_role("teacher"))):
    s = scoring.get_teacher_settings(db, user.id)
    db.commit()
    return _s_out(s)


@router.put("/teacher")
def update_teacher_settings(data: TeacherSettingsIn, db: Session = Depends(get_db),
                            user: User = Depends(require_role("teacher"))):
    s = scoring.get_teacher_settings(db, user.id)
    for k, v in data.model_dump().items():
        setattr(s, k, v)
    db.commit()
    return _s_out(s)


@router.put("/password")
def change_password(data: PasswordChangeIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not verify_password(data.old_password, user.password_hash):
        raise AppError(400, "wrong_old_password")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"ok": True}


@router.put("/preferences")
def update_preferences(data: PreferencesIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if data.language:
        user.language = data.language
    if data.theme:
        user.theme = data.theme
    db.commit()
    return user_out(user)


@router.put("/profile")
def update_profile(data: ProfileIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    user.name = data.name.strip()
    db.commit()
    return user_out(user)
