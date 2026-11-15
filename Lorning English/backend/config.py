import os
from pathlib import Path
from urllib.parse import quote_plus
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR.parent / ".env")
load_dotenv(BASE_DIR / ".env", override=True)


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _build_database_url() -> str:
    """DATABASE_URL berilsa shu ishlatiladi, bo'lmasa DB_* maydonlaridan yig'iladi."""
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        return url
    kind = os.getenv("DB_TYPE", "sqlite").strip().lower()
    name = os.getenv("DB_NAME", "aedu").strip() or "aedu"
    if kind in ("", "sqlite"):
        return f"sqlite:///./{name}.db"
    host = os.getenv("DB_HOST", "localhost").strip() or "localhost"
    user = quote_plus(os.getenv("DB_USER", "").strip())
    password = quote_plus(os.getenv("DB_PASSWORD", ""))
    if kind in ("postgres", "postgresql", "pg"):
        port = os.getenv("DB_PORT", "5432").strip() or "5432"
        driver = "postgresql+psycopg2"
    elif kind in ("mysql", "mariadb"):
        port = os.getenv("DB_PORT", "3306").strip() or "3306"
        driver = "mysql+pymysql"
    else:
        raise SystemExit(f"[XATO] DB_TYPE noto'g'ri: {kind!r} (sqlite | postgresql | mysql)")
    auth = f"{user}:{password}@" if user else ""
    return f"{driver}://{auth}{host}:{port}/{name}"


class Settings:
    DATABASE_URL: str = _build_database_url()
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = _int("ACCESS_TOKEN_EXPIRE_MINUTES", 10080)
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    RESEND_FROM_EMAIL: str = os.getenv("RESEND_FROM_EMAIL", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "").strip().strip('"').strip("'")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "").strip().strip('"').strip("'")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")
    VERCEL_AI_GATEWAY_API_KEY: str = os.getenv("VERCEL_AI_GATEWAY_API_KEY", "").strip().strip('"').strip("'")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "").strip()
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "auto").strip().lower()  # auto | anthropic | openai | gemini
    AI_MODEL: str = os.getenv("AI_MODEL", "").strip()
    # Saytda ko'rsatiladigan qo'shimcha modellar. Format: model yoki provayder:model
    AI_MODELS: str = os.getenv("AI_MODELS", "").strip()
    SMS_PROVIDER: str = os.getenv("SMS_PROVIDER", "").strip().lower()
    SMS_API_KEY: str = os.getenv("SMS_API_KEY", "")
    SMS_API_URL: str = os.getenv("SMS_API_URL", "")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "https://aedu-eight.vercel.app")
    AI_DAILY_LIMIT: int = _int("AI_DAILY_LIMIT", 8)  # Ustoz AI: har bir o'quvchi uchun kunlik limit
    RESUBMIT_PENALTY: float = float(os.getenv("RESUBMIT_PENALTY", "3") or 3)
    REQUIRE_OTP: bool = os.getenv("REQUIRE_OTP", "true").strip().lower() in ("1", "true", "yes", "on")
    APP_TZ_OFFSET: int = _int("APP_TZ_OFFSET", 5)
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    # Telegram bot: BOT_TOKEN (asosiy) yoki eski TELEGRAM_BOT_TOKEN
    TELEGRAM_BOT_TOKEN: str = (os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or "").strip().strip('"').strip("'")
    TELEGRAM_BOT_USERNAME: str = os.getenv("TELEGRAM_BOT_USERNAME", "").strip().lstrip("@")
    TELEGRAM_POLLING: bool = os.getenv("TELEGRAM_POLLING", "true").strip().lower() in ("1", "true", "yes", "on")
    PUBLIC_URL: str = os.getenv("PUBLIC_URL", "").strip()
    ALERTS_INTERVAL_MINUTES: int = _int("ALERTS_INTERVAL_MINUTES", 10)  # avtomatik ota-ona xabarlarini tekshirish oralig'i
    # Birinchi o'qituvchi hisobi (ishga tushganda avtomatik yaratiladi)
    TEACHER_PHONE: str = os.getenv("TEACHER_PHONE", "").strip()
    TEACHER_EMAIL: str = os.getenv("TEACHER_EMAIL", "").strip()
    TEACHER_PASSWORD: str = os.getenv("TEACHER_PASSWORD", "")
    TEACHER_NAME: str = os.getenv("TEACHER_NAME", "O'qituvchi").strip() or "O'qituvchi"


settings = Settings()

if not settings.SECRET_KEY:
    # Faqat DEV uchun. Productionda albatta .env ga SECRET_KEY yozing!
    settings.SECRET_KEY = "dev-insecure-secret-change-me"
    print("[WARN] SECRET_KEY bo'sh. DEV kalit ishlatilmoqda. .env ga SECRET_KEY yozing.")
