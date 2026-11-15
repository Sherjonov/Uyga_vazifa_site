from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

import pymupdf as fitz

TEXT_EXTS = {
    ".txt", ".md", ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".cpp",
    ".cs", ".html", ".css", ".sql", ".json", ".go", ".rs", ".php", ".rb",
}
MAX_ARCHIVE_BYTES = 20 * 1024 * 1024


def extract_text(path: Path, max_chars: int = 12000) -> str:
    extension = path.suffix.lower()
    if extension == ".pdf":
        with fitz.open(str(path)) as document:
            if document.page_count > 100:
                raise ValueError("PDF has too many pages")
            pages = []
            total = 0
            for page in document:
                page_text = page.get_text("text")
                pages.append(page_text[:max_chars - total])
                total += len(page_text)
                if total >= max_chars:
                    break
            text = "\n".join(pages)
    elif extension == ".docx":
        try:
            with ZipFile(path) as archive:
                if sum(entry.file_size for entry in archive.infolist()) > MAX_ARCHIVE_BYTES:
                    raise ValueError("Word document expands beyond the text extraction limit")
                if "word/document.xml" not in archive.namelist():
                    raise ValueError("Invalid Word document")
                root = ElementTree.fromstring(archive.read("word/document.xml"))
        except ElementTree.ParseError as error:
            raise ValueError("Invalid Word document") from error
        namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        text = "\n".join(
            "".join(node.text or "" for node in paragraph.iter(f"{namespace}t"))
            for paragraph in root.iter(f"{namespace}p")
        )
    elif extension == ".zip":
        parts = []
        total_size = 0
        total_chars = 0
        with ZipFile(path) as archive:
            entries = archive.infolist()
            if sum(entry.file_size for entry in entries) > MAX_ARCHIVE_BYTES:
                raise ValueError("Archive expands beyond the text extraction limit")
            for entry in entries:
                member = Path(entry.filename)
                if entry.is_dir() or member.suffix.lower() not in TEXT_EXTS:
                    continue
                total_size += entry.file_size
                if total_size > MAX_ARCHIVE_BYTES:
                    raise ValueError("Archive source files exceed the text extraction limit")
                source = archive.read(entry).decode("utf-8", errors="replace")
                part = f"# --- {entry.filename[:200]} ---\n{source[:max_chars - total_chars]}"
                parts.append(part)
                total_chars += len(part)
                if total_chars >= max_chars:
                    break
        text = "\n\n".join(parts)
    elif extension in TEXT_EXTS:
        text = path.read_text(encoding="utf-8")
    else:
        return ""
    return text.strip()[:max_chars]
