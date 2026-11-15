from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from deps import get_current_user
from messages import AppError
from models.user import User
from services import ai_service, translator

router = APIRouter(prefix="/translate", tags=["translator"])


class TranslateIn(BaseModel):
    text: str = Field(min_length=1, max_length=3000)
    source: str = Field(pattern=r"^(en|uz)$")
    target: str = Field(pattern=r"^(en|uz)$")
    model: Optional[str] = None


@router.post("")
def translate(data: TranslateIn, user: User = Depends(get_current_user)):
    """Inglizcha ⇄ O'zbekcha tarjima."""
    if data.source == data.target or not data.text.strip():
        raise AppError(422, "validation_error")
    if not ai_service.is_configured():
        raise AppError(503, "ai_not_configured")
    try:
        ai_service.validate_model_choice(data.model)
        return {"translation": translator.translate(data.text.strip(), data.source, data.target, data.model)}
    except ai_service.AIError as e:
        raise AppError(503, e.code) from e
