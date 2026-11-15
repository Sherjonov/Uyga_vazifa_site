"""Learning English: bitta fayl bilan hammasini ishga tushirish.

    python main.py              -> backend (8000) + frontend (5173)
    python main.py --demo       -> avval demo ma'lumotlarni qo'shadi
    python main.py --no-frontend
    uvicorn main:app --reload   -> faqat backend (qo'lda)
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
sys.path.insert(0, str(BACKEND))  # backend/ ichidagi barcha modullar shu orqali ulanadi

from contextlib import asynccontextmanager  # noqa: E402

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse, FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

import models  # noqa: E402,F401  (barcha jadvallarni ro'yxatdan o'tkazadi)
import seed  # noqa: E402
from config import settings  # noqa: E402
import migrate  # noqa: E402
from database import Base, engine, SessionLocal  # noqa: E402
from messages import AppError, lang_from_request, t  # noqa: E402
from routers import (  # noqa: E402
    auth, onboarding, groups, grid, attendance, assignments, tests, retake, rating,
    danger_zone, ai_chat, settings as settings_router, roster, books, vocab, translate,
    telegram as telegram_router, parents,
)
from routers import messages as messages_router  # noqa: E402
from services import parent_alerts, telegram_bot  # noqa: E402

for sub in ("pdfs", "slides", "submissions", "books"):
    (settings.UPLOAD_DIR / sub).mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)  # jadvallar ishga tushganda avtomatik yaratiladi
    migrate.run(engine, Base)  # eski bazaga yangi ustunlar qo'shiladi
    with SessionLocal() as db:
        seed.ensure_env_teacher(db)  # .env dagi TEACHER_PHONE / TEACHER_PASSWORD
    telegram_bot.start()   # Telegram bot (BOT_TOKEN): ota-onalar, o'quvchilar, tasdiqlash kodi
    parent_alerts.start()  # ota-onalarga avtomatik xabarlar (vazifa topshirilmadi, xavf zonasi)
    yield
    telegram_bot.stop()
    parent_alerts.stop()


app = FastAPI(title="Learning English API", version="1.0.0", lifespan=lifespan)

origins = {settings.FRONTEND_URL.rstrip("/"), "http://localhost:5173", "http://127.0.0.1:5173"}
app.add_middleware(CORSMiddleware, allow_origins=list(origins), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    lang = lang_from_request(request)
    return JSONResponse(status_code=exc.status, content={"detail": t(exc.key, lang, **exc.fmt), "code": exc.key})


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    lang = lang_from_request(request)
    fields = [{"loc": [str(x) for x in e.get("loc", [])], "msg": str(e.get("msg", ""))} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": t("validation_error", lang), "code": "validation_error", "fields": fields})


for r in (auth, onboarding, groups, grid, attendance, assignments, tests, retake, rating,
          danger_zone, ai_chat, messages_router, settings_router, roster, books, vocab, translate,
          telegram_router, parents):
    app.include_router(r.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}


# Yuklangan fayllar (PDF slaydlari, topshiriqlar)
app.mount("/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")

# Production: `npm run build` dan keyin frontend/dist shu serverdan beriladi
_DIST = FRONTEND / "dist"
if _DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        f = (_DIST / full_path).resolve()
        if full_path and f.is_file() and _DIST in f.parents:
            return FileResponse(f)
        return FileResponse(_DIST / "index.html")


def _npm() -> str | None:
    return shutil.which("npm.cmd" if os.name == "nt" else "npm")


def run() -> None:
    parser = argparse.ArgumentParser(description="Learning English ni ishga tushirish")
    parser.add_argument("--demo", action="store_true", help="demo o'qituvchi, 5 o'quvchi va 1 guruh qo'shish")
    parser.add_argument("--no-frontend", action="store_true", help="faqat backend")
    parser.add_argument("--no-reload", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.demo:
        Base.metadata.create_all(bind=engine)
        migrate.run(engine, Base)
        with SessionLocal() as db:
            seed.create_demo(db)

    front = None
    npm = _npm()
    if not args.no_frontend and (FRONTEND / "package.json").exists():
        if not npm:
            print("[OGOHLANTIRISH] Node.js/npm topilmadi: frontend ishga tushirilmadi (https://nodejs.org).")
        else:
            if not (FRONTEND / "node_modules").exists():
                print("[Learning English] frontend paketlari o'rnatilmoqda (npm install)...")
                subprocess.run([npm, "install"], cwd=FRONTEND, check=False)
            front = subprocess.Popen([npm, "run", "dev"], cwd=FRONTEND)
            print("[Learning English] Sayt: http://localhost:5173   |   API hujjati: http://localhost:8000/docs")

    import uvicorn
    try:
        uvicorn.run("main:app", host=args.host, port=args.port, reload=not args.no_reload, reload_dirs=[str(BACKEND)])
    finally:
        if front and front.poll() is None:  
            front.terminate()


if __name__ == "__main__":
    run()
