"""Bot xabarlari matni (HTML). Faqat statistika lug'atidan (child_stats.overview) matn yasaydi."""
from typing import Optional

from services.child_stats import fmt_dt, num
from services.telegram_api import esc

MAX_LINES = 12


def clip(text: str, limit: int = 3900) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def short(title: str, n: int = 42) -> str:
    title = " ".join((title or "").split())
    return title if len(title) <= n else title[: n - 1] + "…"


def _place(rank: Optional[int], total: int) -> str:
    return f"<b>{rank}-o'rin</b> ({total} kishidan)" if rank else "—"


def _hw_line(r: dict) -> str:
    t = esc(short(r["title"]))
    st = r["status"]
    if st == "graded":
        return f"· {t}: ✅ <b>{num(r['score'])}/{num(r['max'])}</b> ball"
    if st == "checking":
        return f"· {t}: 📥 tekshirilmoqda" + (f" (muddat {fmt_dt(r['due_at'])})" if r["due_at"] else "")
    if st == "missed":
        return f"· {t}: ❌ topshirilmagan" + (f" (muddat {fmt_dt(r['due_at'])})" if r["due_at"] else "")
    return f"· {t}: ⏳ muddat {fmt_dt(r['due_at'])}" if r["due_at"] else f"· {t}: ⏳ kutilmoqda"


def render_rank(ov: dict) -> str:
    name = esc(ov["student"]["name"])
    lines = [f"🏆 <b>{name}</b> — reyting"]
    for g in ov["groups"]:
        lines.append(f"👥 {esc(g['name'])}: {_place(g['rank'], g['total'])}")
    if not ov["groups"]:
        lines.append("Hali birorta guruhga qo'shilmagan.")
    if ov["overall"]:
        lines.append(f"🌍 Umumiy reyting: {_place(ov['overall']['rank'], ov['overall']['total'])}")
    lines.append(f"⭐ Jami ball: <b>{num(ov['score']['total'])}</b>")
    return "\n".join(lines)


def render_status(ov: dict) -> str:
    name = esc(ov["student"]["name"])
    sc, hw, tk, ts, at = ov["score"], ov["homework"], ov["tasks"], ov["tests"], ov["attendance"]
    lines = [f"📊 <b>{name}</b> — holati", ""]
    for g in ov["groups"]:
        lines.append(f"👥 {esc(g['name'])}: {_place(g['rank'], g['total'])}")
    if ov["overall"]:
        lines.append(f"🌍 Umumiy reyting: {_place(ov['overall']['rank'], ov['overall']['total'])}")
    parts = [f"testlar {num(sc['tests'])}", f"vazifa/topshiriq {num(sc['assignments'])}"]
    if sc["grid"]:
        parts.append(f"jadval {num(sc['grid'])}")
    pen = sc["penalties"] + sc["resubmits"]
    if pen:
        parts.append(f"jarima −{num(pen)}")
    lines.append(f"⭐ Jami ball: <b>{num(sc['total'])}</b> ({' · '.join(parts)})")

    lines += ["", f"🏠 <b>Uyga vazifalar:</b> {hw['done']}/{hw['total']} bajarilgan"]
    if hw["total"]:
        lines.append(f"· ✅ baholangan: {hw['graded']} · 📥 tekshirilmoqda: {hw['checking']}")
        lines.append(f"· ❌ topshirilmagan: <b>{hw['missed']}</b> · ⏳ muddati kelmagan: {hw['pending']}")
        if hw["max_points"]:
            lines.append(f"· Olingan ball: <b>{num(hw['points'])}/{num(hw['max_points'])}</b>")

    lines += ["", f"⚡ <b>Topshiriqlar:</b> {tk['done']}/{tk['total']} bajarilgan"]
    if tk["total"]:
        if tk["missed"]:
            lines.append(f"· ❌ bajarilmagan: <b>{tk['missed']}</b>")
        if tk["max_points"]:
            lines.append(f"· Olingan ball: <b>{num(tk['points'])}/{num(tk['max_points'])}</b>")

    lines.append("")
    if ts["taken"]:
        lines.append(f"📝 <b>Testlar:</b> o'rtacha <b>{num(ts['avg_percent'])}%</b> ({ts['taken']} ta topshirilgan"
                     + (f", {ts['not_taken']} ta qolgan" if ts["not_taken"] else "") + ")")
    elif ts["available"]:
        lines.append(f"📝 <b>Testlar:</b> hali topshirilmagan ({ts['available']} ta mavjud)")
    else:
        lines.append("📝 <b>Testlar:</b> hali yo'q")
    if at["total"]:
        lines.append(f"📅 <b>Davomat:</b> ✅ {at['present']} keldi · ❌ {at['absent']} kelmadi · 🟡 {at['excused']} sababli")
    else:
        lines.append("📅 <b>Davomat:</b> hali belgilanmagan")
    return clip("\n".join(lines))


def render_homework(ov: dict) -> str:
    name = esc(ov["student"]["name"])
    hw, tk = ov["homework"], ov["tasks"]
    lines = [f"🏠 <b>Uyga vazifalar</b> — {name}"]
    if not hw["rows"]:
        lines.append("· Hali vazifa berilmagan")
    for r in hw["rows"][:MAX_LINES]:
        lines.append(_hw_line(r))
        if r["status"] == "graded" and r["comment"]:
            lines.append(f"   💬 {esc(short(r['comment'], 80))}")
    if len(hw["rows"]) > MAX_LINES:
        lines.append(f"… va yana {len(hw['rows']) - MAX_LINES} ta")
    lines.append("")
    lines.append(f"Bajarilgan: <b>{hw['done']}/{hw['total']}</b> · Topshirilmagan: <b>{hw['missed']}</b>"
                 + (f" · Ball: <b>{num(hw['points'])}/{num(hw['max_points'])}</b>" if hw["max_points"] else ""))
    lines += ["", "⚡ <b>Topshiriqlar</b>"]
    if not tk["rows"]:
        lines.append("· Hali topshiriq berilmagan")
    for r in tk["rows"][:MAX_LINES]:
        lines.append(_hw_line(r))
    if len(tk["rows"]) > MAX_LINES:
        lines.append(f"… va yana {len(tk['rows']) - MAX_LINES} ta")
    if tk["total"]:
        lines.append("")
        lines.append(f"Bajarilgan: <b>{tk['done']}/{tk['total']}</b>"
                     + (f" · Ball: <b>{num(tk['points'])}/{num(tk['max_points'])}</b>" if tk["max_points"] else ""))
    return clip("\n".join(lines))


def render_tests(ov: dict) -> str:
    name = esc(ov["student"]["name"])
    ts = ov["tests"]
    lines = [f"📝 <b>Testlar</b> — {name}"]
    if not ts["rows"]:
        lines.append("· Hali test berilmagan")
    for r in ts["rows"][:MAX_LINES]:
        if r["percent"] is None:
            lines.append(f"· {esc(short(r['title']))}: ⏳ topshirilmagan")
        else:
            lines.append(f"· {esc(short(r['title']))}: ✅ <b>{num(r['percent'])}%</b> ({r['correct']}/{r['total']})")
    if ts["taken"]:
        lines += ["", f"O'rtacha natija: <b>{num(ts['avg_percent'])}%</b> · Topshirilgan: {ts['taken']}/{ts['available']}"]
    return clip("\n".join(lines))


def render_attendance(ov: dict) -> str:
    name = esc(ov["student"]["name"])
    at = ov["attendance"]
    lines = [f"📅 <b>Davomat</b> — {name}"]
    if not at["total"]:
        lines.append("· Hali davomat belgilanmagan")
        return "\n".join(lines)
    lines.append(f"✅ Keldi: <b>{at['present']}</b>")
    lines.append(f"❌ Kelmadi: <b>{at['absent']}</b>")
    lines.append(f"🟡 Sababli: <b>{at['excused']}</b>")
    if at["recent_absent"]:
        lines += ["", "So'nggi kelmagan kunlar:"]
        for r in at["recent_absent"]:
            t = f" — {esc(short(r['title'], 40))}" if r["title"] else ""
            lines.append(f"· {r['date'].strftime('%d.%m.%Y')}{t}")
    return "\n".join(lines)


def render_reviewed(student_name: str, title: str, score: float, max_score: float, comment: Optional[str],
                    for_parent: bool) -> str:
    who = f"Farzandingiz <b>{esc(student_name)}</b>ning" if for_parent else f"<b>{esc(student_name)}</b>, sizning"
    lines = [f"✅ {who} «{esc(short(title, 60))}» vazifasi baholandi: <b>{num(score)}/{num(max_score)}</b>"]
    if comment:
        lines.append(f"💬 Mentor: {esc(short(comment, 300))}")
    return "\n".join(lines)
