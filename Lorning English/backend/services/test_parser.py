"""PDF matnidan test savollarini ajratish: avval AI, bo'lmasa oddiy format parser."""
import json
import re
from typing import List, Optional, Tuple

from services import ai_service

Q_RE = re.compile(r"^\s*(\d{1,3})\s*[\.\)]\s*(.+)$")
OPT_MARK_RE = re.compile(r"(?:^|\s)\(?([A-Ea-e])[\)\.]\s+")
ANS_INLINE_RE = re.compile(r"^\s*(?:javob|answer|ответ|to'?g'?ri javob)\s*[:\-]?\s*\(?([A-Ea-e])\)?\s*$", re.I)
HEADER_RE = re.compile(
    r"^\s*(javoblar|javob kaliti|kalitlar|kalit|to'?g'?ri javoblar|answers?|answer key|key|ответы|ключ)\s*[:.\-]*\s*$", re.I
)
KEY_PAIR_RE = re.compile(r"(\d{1,3})\s*[\-\.\):=]?\s*([A-Ea-e])\b")
KEY_LINE_RE = re.compile(r"^\s*(?:\d{1,3}\s*[\-\.\):=]?\s*[A-Ea-e]\s*[,;\s]*)+$")


def _options_in_line(line: str) -> List[Tuple[str, str]]:
    matches = list(OPT_MARK_RE.finditer(line))
    if not matches:
        return []
    letters = [m.group(1).upper() for m in matches]
    # Variantlar ketma-ket (A, B, C...) bo'lishi kerak
    if letters != [chr(ord(letters[0]) + i) for i in range(len(letters))]:
        matches, letters = matches[:1], letters[:1]
    # Qator aynan variantdan boshlanishi kerak (savol matni ichidagi "A." ni chetlab o'tish)
    if matches[0].start() > 0 and line[: matches[0].start()].strip():
        return []
    out = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(line)
        out.append((letters[i], line[m.end():end].strip()))
    return out


def _split_key(lines: List[str]) -> Tuple[List[str], dict]:
    key_start = None
    for i, l in enumerate(lines):
        if HEADER_RE.match(l.strip()):
            key_start = i
    key_lines: List[str] = []
    if key_start is not None:
        body, key_lines = lines[:key_start], lines[key_start + 1:]
    else:
        body = list(lines)
        j = len(body)
        while j > 0 and (not body[j - 1].strip() or KEY_LINE_RE.match(body[j - 1])):
            j -= 1
        tail = body[j:]
        if sum(len(KEY_PAIR_RE.findall(x)) for x in tail) >= 3:
            body, key_lines = body[:j], tail
    key = {}
    for l in key_lines:
        for n, letter in KEY_PAIR_RE.findall(l):
            key[int(n)] = letter.upper()
    return body, key


def parse_plain(text: str) -> List[dict]:
    lines = text.replace("\r", "").split("\n")
    body, key = _split_key(lines)

    items: List[dict] = []
    cur: Optional[dict] = None
    last = "q"
    for raw in body:
        line = raw.strip()
        if not line:
            continue
        m_ans = ANS_INLINE_RE.match(line)
        if m_ans and cur is not None:
            cur["answer"] = m_ans.group(1).upper()
            continue
        opts = _options_in_line(line) if cur is not None else []
        if opts:
            for letter, txt in opts:
                cur["options"].append(txt)
                cur["letters"].append(letter)
            last = "opt"
            continue
        m_q = Q_RE.match(line)
        if m_q and (cur is None or cur["options"] or int(m_q.group(1)) == cur["num"] + 1):
            cur = {"num": int(m_q.group(1)), "text": m_q.group(2).strip(), "options": [], "letters": [], "answer": None}
            items.append(cur)
            last = "q"
            continue
        if cur is not None:
            if last == "opt" and cur["options"]:
                cur["options"][-1] += " " + line
            else:
                cur["text"] += " " + line

    result = []
    for it in items:
        if len(it["options"]) < 2:
            continue
        options, correct = [], None
        for idx, opt in enumerate(it["options"]):
            o = opt.strip()
            if o.endswith("*") or o.startswith("*") or o.endswith("(+)"):
                correct = idx
                o = o.strip("*").replace("(+)", "").strip()
            options.append(o)
        letter = it["answer"] or key.get(it["num"])
        if letter is not None and correct is None:
            pos = ord(letter) - 65
            if 0 <= pos < len(options):
                correct = pos
        result.append({"text": it["text"].strip(), "options": options[:6], "correct_index": correct})
    return result


AI_PROMPT = (
    "Quyidagi matn test PDF faylidan olingan. Undagi BARCHA test savollarini JSON massiviga aylantir.\n"
    'Format: [{"text": "savol matni", "options": ["variant 1", "variant 2", ...], "correct_index": 0}]\n'
    "Qoidalar: correct_index 0 dan boshlanadi. Variant harflarini (A), B)...) matndan olib tashla. "
    "Javob kaliti matnda bo'lsa undan foydalan, bo'lmasa to'g'ri javobni o'zing aniqla. "
    "Faqat JSON massivni qaytar, boshqa hech narsa yozma.\n\nMATN:\n"
)


def parse_with_ai(text: str) -> List[dict]:
    raw = ai_service.complete("Sen test savollarini tuzilmaga o'giruvchi yordamchisan.", AI_PROMPT + text[:45000], max_tokens=8000)
    start, end = raw.find("["), raw.rfind("]")
    if start == -1 or end == -1:
        return []
    data = json.loads(raw[start:end + 1])
    out = []
    for q in data:
        try:
            options = [str(o).strip() for o in q["options"] if str(o).strip()][:6]
            idx = int(q["correct_index"])
            if len(options) >= 2 and str(q["text"]).strip() and 0 <= idx < len(options):
                out.append({"text": str(q["text"]).strip(), "options": options, "correct_index": idx})
        except (KeyError, TypeError, ValueError):
            continue
    return out


def parse_questions(text: str) -> Tuple[List[dict], str]:
    """-> (savollar, usul) usul: 'ai' | 'plain'"""
    if ai_service.is_configured():
        try:
            qs = parse_with_ai(text)
            if qs:
                return qs, "ai"
        except Exception as e:  # AI xatosi bo'lsa oddiy parserga o'tamiz
            print(f"[test_parser] AI parse failed: {e}")
    return parse_plain(text), "plain"
