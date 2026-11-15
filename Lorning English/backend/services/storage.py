import re
import uuid
from pathlib import Path

from fastapi import UploadFile

from config import settings
from messages import AppError

DOC_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx",
            ".py", ".zip", ".html", ".css", ".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".cpp", ".cs",
            ".sql", ".json", ".md", ".go", ".rs", ".php", ".rb"}
TEXT_EXTS = {".txt", ".py", ".html", ".css", ".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".cpp", ".cs",
             ".sql", ".json", ".md", ".go", ".rs", ".php", ".rb"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}

_MAGIC = {
    ".pdf": [b"%PDF"],
    ".png": [b"\x89PNG"],
    ".jpg": [b"\xff\xd8"],
    ".jpeg": [b"\xff\xd8"],
    ".webp": [b"RIFF"],
    ".zip": [b"PK"],
    ".docx": [b"PK"],
    ".xlsx": [b"PK"],
    ".pptx": [b"PK"],
    ".doc": [b"\xd0\xcf\x11\xe0"],
    ".xls": [b"\xd0\xcf\x11\xe0"],
    ".ppt": [b"\xd0\xcf\x11\xe0"],
}


def save_upload(file: UploadFile, subdir: str, allowed=None, max_mb: int = 20) -> str:
    """Faylni xavfsiz saqlaydi va uploads/ ga nisbatan yo'lni qaytaradi."""
    allowed = allowed or DOC_EXTS
    original = file.filename or ""
    ext = Path(original).suffix.lower()
    if ext not in allowed:
        raise AppError(400, "file_type_not_allowed")

    stem = re.sub(r"[^A-Za-z0-9_-]", "_", Path(original).stem)[:40] or "file"
    folder = settings.UPLOAD_DIR / subdir
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex[:12]}_{stem}{ext}"
    dest = folder / name
    limit = max_mb * 1024 * 1024
    size = 0
    first = True
    try:
        with open(dest, "wb") as out:
            while True:
                chunk = file.file.read(1024 * 256)
                if not chunk:
                    break
                if first:
                    first = False
                    magics = _MAGIC.get(ext)
                    if magics and not any(chunk.startswith(m) for m in magics):
                        raise AppError(400, "file_type_not_allowed")
                    if ext in TEXT_EXTS and b"\x00" in chunk[:1024]:
                        raise AppError(400, "file_type_not_allowed")
                size += len(chunk)
                if size > limit:
                    raise AppError(413, "file_too_large", mb=max_mb)
                out.write(chunk)
        if size == 0:
            raise AppError(400, "file_required")
    except Exception:
        dest.unlink(missing_ok=True)
        raise
    return f"{subdir}/{name}"


def abs_path(rel: str) -> Path:
    return settings.UPLOAD_DIR / rel


def delete_file(rel) -> None:
    if rel:
        try:
            abs_path(rel).unlink(missing_ok=True)
        except OSError:
            pass
