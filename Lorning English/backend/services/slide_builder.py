"""PDF sahifalaridan chiroyli slayd tuzadi: sarlavha, matn, ro'yxat, kod bloki, rasm va belgilab bo'ladigan test savollari."""
import re
import statistics
from pathlib import Path
from typing import Dict, List, Optional

from services.test_parser import ANS_INLINE_RE, Q_RE, _options_in_line, _split_key

MONO_HINTS = ("mono", "courier", "consolas", "menlo", "typewriter", "fira", "hack", "cascadia", "sourcecode", "inconsolata", "lucidaconsole")
BULLET_RE = re.compile(r"^\s*(?:[•●◦▪■▸►‣∙\u2022\-–—*]|\d{1,2}[.)])\s+(.+)$")
SKIP_RE = re.compile(r"^\s*(savol|question|вопрос)\s*\d+\s*(/|из|of)\s*\d+\s*$", re.I)


def _is_mono(font: str) -> bool:
    f = (font or "").lower().replace(" ", "").replace("-", "")
    return any(h in f for h in MONO_HINTS)


def _clean_q(text: str) -> str:
    return re.sub(r"^[^\w(]+", "", text or "").strip()


def _newq(text: str, code_buf: List[str], num: Optional[int] = None) -> dict:
    return {"num": num, "text": _clean_q(text), "code": "\n".join(code_buf) if code_buf else None, "options": [], "answer": None}


def _quiz(lines: List[dict]) -> List[dict]:
    qs: List[dict] = []
    cur: Optional[dict] = None
    intro: List[str] = []
    code_buf: List[str] = []
    for ln in lines:
        t = ln["text"].strip()
        if not t:
            continue
        if ln["mono"]:
            raw = ln["text"].rstrip()
            if cur is None:
                code_buf.append(raw)
            elif not cur["options"]:
                cur["code"] = (cur["code"] + "\n" if cur["code"] else "") + raw
            else:
                cur["options"][-1] += " " + t
            continue
        if SKIP_RE.match(t):
            continue
        m_ans = ANS_INLINE_RE.match(t)
        if m_ans and cur is not None:
            cur["answer"] = m_ans.group(1).upper()
            continue
        opts = _options_in_line(t)
        if opts:
            if cur is None:
                cur = _newq(intro.pop() if intro else "", code_buf)
                code_buf = []
                qs.append(cur)
            cur["options"].extend(txt for _, txt in opts)
            continue
        mq = Q_RE.match(t)
        if mq and (cur is None or cur["options"]):
            cur = _newq(mq.group(2), code_buf, int(mq.group(1)))
            code_buf = []
            qs.append(cur)
            continue
        if cur is not None and cur["options"]:
            if t.endswith("?"):
                cur = _newq(t, [])
                qs.append(cur)
            else:
                cur["options"][-1] += " " + t
            continue
        if cur is not None:
            cur["text"] += " " + t
            continue
        intro.append(t)

    out = []
    for q in qs:
        if len(q["options"]) < 2:
            continue
        options, correct = [], None
        for i, o in enumerate(q["options"][:6]):
            o = o.strip()
            if o.endswith("*") or o.startswith("*") or o.endswith("(+)"):
                correct = i
                o = o.strip("*").replace("(+)", "").strip()
            options.append(o)
        if q["answer"] and correct is None:
            pos = ord(q["answer"]) - 65
            correct = pos if 0 <= pos < len(options) else None
        out.append({"num": q["num"], "text": q["text"], "code": q["code"], "options": options, "correct_index": correct})
    return out


def build_content(lines: List[dict], images: Optional[List[str]] = None) -> Optional[dict]:
    """lines: [{text,size,mono,bold,y,x}] o'qish tartibida. -> {"title","blocks","quiz","images"} yoki None"""
    images = images or []
    lines = [l for l in lines if l["text"].strip()]
    if not lines:
        return {"title": None, "blocks": [], "quiz": None, "images": images} if images else None

    # kod qatorlaridagi chekinishni x koordinatadan tiklaymiz
    mono_x = [l["x"] for l in lines if l["mono"] and "x" in l]
    if mono_x:
        base_x = min(mono_x)
        for l in lines:
            if l["mono"] and "x" in l and not l["text"].startswith(" "):
                indent = int(round((l["x"] - base_x) / max(1.0, 0.6 * l["size"])))
                l["text"] = " " * max(0, indent) + l["text"].lstrip()

    weighted = [l["size"] for l in lines if not l["mono"] for _ in range(max(1, len(l["text"].strip()) // 8))]
    base = statistics.median(weighted) if weighted else (lines[0]["size"] or 12)

    # sarlavha: eng katta shrift (asosiy matndan kamida 1.3 baravar)
    title = None
    rest = list(lines)
    for i, l in enumerate(rest):
        if not l["mono"] and l["size"] >= base * 1.3:
            parts, j = [l["text"].strip()], i + 1
            while j < len(rest) and not rest[j]["mono"] and abs(rest[j]["size"] - l["size"]) < 0.6:
                parts.append(rest[j]["text"].strip())
                j += 1
            title = " ".join(parts)
            rest = rest[:i] + rest[j:]
            break

    option_lines = sum(1 for l in rest if not l["mono"] and _options_in_line(l["text"].strip()))
    if option_lines >= 2 or any(len(_options_in_line(l["text"].strip())) >= 2 for l in rest if not l["mono"]):
        qs = _quiz(rest)
        if qs:
            return {"title": title, "blocks": [], "quiz": qs, "images": images}

    blocks: List[dict] = []
    code_buf: List[str] = []
    prev_y, prev_size = None, None

    def flush_code():
        if code_buf:
            blocks.append({"type": "code", "text": "\n".join(code_buf)})
            code_buf.clear()

    for l in rest:
        t = l["text"].strip()
        if l["mono"]:
            code_buf.append(l["text"].rstrip())
            prev_y = None
            continue
        flush_code()
        gap_small = prev_y is not None and abs(l["y"] - prev_y) < 1.7 * max(l["size"], 1)
        m = BULLET_RE.match(t)
        last = blocks[-1] if blocks else None
        if l["bold"] and l["size"] >= base * 1.12 and not m:
            blocks.append({"type": "heading", "text": t})
        elif m:
            item = m.group(1).strip()
            if last and last["type"] == "bullets":
                last["items"].append(item)
            else:
                blocks.append({"type": "bullets", "items": [item]})
        elif last and last["type"] == "bullets" and gap_small and not re.search(r"[.!?:;]$", last["items"][-1]):
            last["items"][-1] += " " + t
        elif last and last["type"] == "para" and gap_small and abs((prev_size or l["size"]) - l["size"]) < 0.8:
            last["text"] += " " + t
        else:
            blocks.append({"type": "para", "text": t})
        prev_y, prev_size = l["y"], l["size"]
    flush_code()
    return {"title": title, "blocks": blocks, "quiz": None, "images": images}


def apply_answer_key(pages: List[Optional[dict]], all_lines: List[str]) -> None:
    """PDF oxirida javoblar kaliti ("1-B 2-A ...") bo'lsa, raqamlangan savollarga qo'llaydi."""
    _, key = _split_key(all_lines)
    if not key:
        return
    qs = [q for c in pages if c and c.get("quiz") for q in c["quiz"]]
    nums = [q["num"] for q in qs if q["num"] is not None]
    if len(nums) != len(set(nums)):
        return
    for q in qs:
        if q["correct_index"] is None and q["num"] in key:
            pos = ord(key[q["num"]]) - 65
            if 0 <= pos < len(q["options"]):
                q["correct_index"] = pos


# ----------------------------- PyMuPDF qismi -----------------------------

def _extract_lines(page) -> List[dict]:
    out = []
    for b in page.get_text("dict").get("blocks", []):
        if b.get("type") != 0:
            continue
        for l in b.get("lines", []):
            spans = l.get("spans", [])
            text = "".join(s.get("text", "") for s in spans)
            real = [s for s in spans if s.get("text", "").strip()]
            if not text.strip() or not real:
                continue
            total = sum(len(s["text"]) for s in real)
            mono_chars = sum(len(s["text"]) for s in real if _is_mono(s.get("font", "")))
            out.append({
                "text": text.rstrip(), "size": float(max(s["size"] for s in real)), "mono": mono_chars >= 0.6 * total,
                "bold": any((s.get("flags", 0) & 16) or "bold" in s.get("font", "").lower() for s in real),
                "y": float(l["bbox"][1]), "x": float(l["bbox"][0]),
            })
    out.sort(key=lambda r: (round(r["y"] / 2), r["x"]))
    return out


def _extract_images(doc, page, out_dir: Path, number: int) -> List[str]:
    import pymupdf as fitz
    names: List[str] = []
    area = page.rect.width * page.rect.height
    for k, info in enumerate(page.get_images(full=True)):
        if len(names) >= 3:
            break
        try:
            xref = info[0]
            rects = page.get_image_rects(xref)
            if rects and max(r.width * r.height for r in rects) > 0.85 * area:
                continue  # butun sahifa fon rasmi
            pix = fitz.Pixmap(doc, xref)
            if pix.width < 80 or pix.height < 80:
                continue
            if pix.alpha:
                data, ext = pix.tobytes("png"), "png"
            else:
                if pix.n - pix.alpha > 3:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                data, ext = pix.tobytes("jpeg"), "jpg"
            name = f"p{number:03d}_i{k}.{ext}"
            (out_dir / name).write_bytes(data)
            names.append(name)
        except Exception:
            continue
    return names


def build_deck(pdf_path: Path, out_dir: Path, zoom: float = 1.6, max_pages: int = 300) -> List[Dict]:
    """Har bir sahifa uchun: JPEG rasm (asl ko'rinish) + qurilgan slayd mazmuni. -> [{"image","content"}]"""
    import pymupdf as fitz
    doc = fitz.open(str(pdf_path))
    try:
        if doc.page_count == 0 or doc.page_count > max_pages:
            raise ValueError("bad page count")
        out_dir.mkdir(parents=True, exist_ok=True)
        deck, contents, all_lines = [], [], []
        matrix = fitz.Matrix(zoom, zoom)
        for i in range(doc.page_count):
            page = doc[i]
            image = f"p{i + 1:03d}.jpg"
            (out_dir / image).write_bytes(page.get_pixmap(matrix=matrix, alpha=False).tobytes("jpeg"))
            try:
                lines = _extract_lines(page)
                all_lines.extend(l["text"] for l in lines)
                content = build_content(lines, _extract_images(doc, page, out_dir, i + 1))
            except Exception:
                content = None  # slayd qurib bo'lmasa, faqat rasm ko'rsatiladi
            contents.append(content)
            deck.append({"image": image, "content": content})
        try:
            apply_answer_key(contents, all_lines)
        except Exception:
            pass
        return deck
    finally:
        doc.close()
