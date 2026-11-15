from pathlib import Path
from typing import List

import pymupdf as fitz

MAX_PAGES = 300


def pdf_to_slides(pdf_path: Path, out_dir: Path, zoom: float = 1.6) -> List[str]:
    """Har bir sahifani JPEG rasmga o'giradi. Fayl nomlari ro'yxatini qaytaradi."""
    doc = fitz.open(str(pdf_path))
    try:
        if doc.page_count == 0 or doc.page_count > MAX_PAGES:
            raise ValueError("bad page count")
        out_dir.mkdir(parents=True, exist_ok=True)
        names = []
        matrix = fitz.Matrix(zoom, zoom)
        for i in range(doc.page_count):
            pix = doc[i].get_pixmap(matrix=matrix, alpha=False)
            name = f"p{i + 1:03d}.jpg"
            (out_dir / name).write_bytes(pix.tobytes("jpeg"))
            names.append(name)
        return names
    finally:
        doc.close()


def pdf_to_text(pdf_path: Path) -> str:
    doc = fitz.open(str(pdf_path))
    try:
        return "\n".join(page.get_text("text") for page in doc)
    finally:
        doc.close()
