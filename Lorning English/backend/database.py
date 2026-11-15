from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import settings

_url = settings.DATABASE_URL
if _url.startswith("postgres://"):
    _url = _url.replace("postgres://", "postgresql://", 1)

_connect_args = {"check_same_thread": False} if _url.startswith("sqlite") else {}
try:
    engine = create_engine(_url, connect_args=_connect_args, pool_pre_ping=True)
except ModuleNotFoundError as e:  # PostgreSQL/MySQL drayveri o'rnatilmagan
    hint = {"psycopg2": "pip install psycopg2-binary", "pymysql": "pip install pymysql"}.get(e.name, f"pip install {e.name}")
    raise SystemExit(f"[XATO] Ma'lumotlar bazasi drayveri topilmadi ({e.name}). O'rnating: python -m {hint}")
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass
