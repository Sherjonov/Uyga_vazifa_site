from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from deps import get_db, require_role, get_group_for_teacher
from models.user import User
from services import student_automation

router = APIRouter(prefix="/danger-zone", tags=["danger-zone"])


@router.get("")
def danger_zone(group_id: Optional[int] = None, db: Session = Depends(get_db),
                user: User = Depends(require_role("teacher"))):
    """Ko'rsatkichi past o'quvchilarni aniqlaydi va xavfga ilk kirishda ota-onasiga xabar beradi."""
    if group_id:
        get_group_for_teacher(db, group_id, user)
    return student_automation.danger_zone(db, user, group_id)
