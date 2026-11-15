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
    vc = ov.get("vocab") or {}
    if vc.get("total"):
        fin = ""
        if vc["final_total"]:
            fin = " · 🏁 yakuniy test: " + ("✅ o'tgan" if vc["final_passed"] else "hali topshirilmagan")
        lines.append(f"📖 <b>Lug'at:</b> {vc['passed']}/{vc['total']} unit topshirilgan (ball: <b>{num(vc['score'])}</b>){fin}")
    else:
        lines.append("📖 <b>Lug'at:</b> hali yo'q")
    if at["total"]:
        lines.append(f"📅 <b>Davomat:</b> ✅ {at['present']} keldi · ⏰ {at['late']} kech qoldi · "
                     f"❌ {at['absent']} kelmadi · 🟡 {at['excused']} sababli")
    else:
        lines.append("📅 <b>Davomat:</b> hali belgilanmagan")
    return clip("\n".join(lines))


def _pct(part: float, whole: float) -> Optional[float]:
    return round(part * 100 / whole, 1) if whole else None


def render_level(ov: dict) -> str:
    """Bilim darajasi: testlar, uyga vazifa, lug'at va davomat ko'rsatkichlaridan umumiy baho."""
    name = esc(ov["student"]["name"])
    hw, ts, at, vc, sc = ov["homework"], ov["tests"], ov["attendance"], ov.get("vocab") or {}, ov["score"]
    hw_pct = _pct(hw["points"], hw["max_points"])
    vc_pct = _pct(vc.get("passed", 0), vc.get("total", 0))
    at_pct = _pct(at["present"] + at["late"] + at["excused"], at["total"])
    signals = [v for v in (ts["avg_percent"], hw_pct, vc_pct, at_pct) if v is not None]
    avg = sum(signals) / len(signals) if signals else None
    if avg is None:
        level = "ma'lumot yetarli emas"
    elif avg >= 85:
        level = "🌟 <b>A'lo</b>"
    elif avg >= 70:
        level = "👍 <b>Yaxshi</b>"
    elif avg >= 55:
        level = "🙂 <b>Qoniqarli</b>"
    else:
        level = "⚠️ <b>Past</b> — e'tibor kerak"
    lines = [f"🎓 <b>{name}</b> — bilim darajasi", "", f"Umumiy daraja: {level}"
             + (f" ({num(avg)}%)" if avg is not None else ""), ""]
    lines.append("📝 Testlar: " + (f"o'rtacha <b>{num(ts['avg_percent'])}%</b> ({ts['taken']} ta)" if ts["taken"] else "hali topshirilmagan"))
    lines.append("🏠 Uyga vazifa: " + (f"<b>{num(hw['points'])}/{num(hw['max_points'])}</b> ball ({num(hw_pct)}%)" if hw_pct is not None
                                       else "hali baholanmagan") + f" · topshirilmagan: <b>{hw['missed']}</b>")
    lines.append("📖 Lug'at: " + (f"<b>{vc['passed']}/{vc['total']}</b> unit ({num(vc_pct)}%)" if vc.get("total") else "hali yo'q"))
    lines.append("📅 Davomat: " + (f"<b>{num(at_pct)}%</b> qatnashgan ({at['absent']} marta kelmagan, {at['late']} marta kech qolgan)"
                                   if at_pct is not None else "hali belgilanmagan"))
    graded = [r for r in hw["rows"] if r["status"] == "graded"][:3]
    if graded:
        lines += ["", "So'nggi baholangan vazifalar:"] + [_hw_line(r) for r in graded]
    lines += ["", f"⭐ Jami ball: <b>{num(sc['total'])}</b>"]
    for g in ov["groups"]:
        lines.append(f"👥 {esc(g['name'])}: {_place(g['rank'], g['total'])}")
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
    lines.append(f"⏰ Kech qoldi: <b>{at['late']}</b>")
    lines.append(f"❌ Kelmadi: <b>{at['absent']}</b>")
    lines.append(f"🟡 Sababli: <b>{at['excused']}</b>")
    if at["recent_absent"]:
        lines += ["", "So'nggi kelmagan kunlar:"]
        for r in at["recent_absent"]:
            t = f" — {esc(short(r['title'], 40))}" if r["title"] else ""
            lines.append(f"· {r['date'].strftime('%d.%m.%Y')}{t}")
    return "\n".join(lines)


MOTIVATION = {
    "high": ["Ajoyib natija! Shu tempda davom eting, siz zo'rsiz! 🌟", "Barakalla! Mehnatingiz samara berdi. 🚀",
             "A'lo! Bunday natija faqat tirishqoq o'quvchilarga nasib qiladi. 👏"],
    "mid": ["Yaxshi natija! Biroz ko'proq mashq qilsangiz, a'loga chiqasiz. 💪", "Yaxshi ketyapsiz! Xatolar ustida ishlang, keyingisi yanada yaxshi bo'ladi. 📈"],
    "low": ["Xafa bo'lmang, har bir xato — o'rganish imkoni. Keyingi safar albatta yaxshiroq bo'ladi! 🌱",
            "Bu hali oxiri emas! Mentor izohini o'qib, qayta urinib ko'ring — siz uddalaysiz. 💫"],
}


def motivation(score: float, max_score: float, for_parent: bool = False, salt: int = 0) -> str:
    pct = score * 100 / max_score if max_score else 0
    pool = MOTIVATION["high" if pct >= 85 else "mid" if pct >= 60 else "low"]
    text = pool[salt % len(pool)]
    if for_parent:
        text = {"high": "Farzandingiz juda yaxshi o'qiyapti — uni rag'batlantiring! 🌟",
                "mid": "Farzandingiz yaxshi ketyapti. Uyda biroz qo'llab-quvvatlasangiz, natija yanada yaxshilanadi. 💪",
                "low": "Farzandingizga ko'proq e'tibor va qo'llab-quvvatlash kerak. Birga takrorlashga undang. 🌱"}["high" if pct >= 85 else "mid" if pct >= 60 else "low"]
    return text


def render_reviewed(student_name: str, title: str, score: float, max_score: float, comment: Optional[str],
                    for_parent: bool, motivation_text: Optional[str] = None) -> str:
    who = f"Farzandingiz <b>{esc(student_name)}</b>ning" if for_parent else f"<b>{esc(student_name)}</b>, sizning"
    pct = round(score * 100 / max_score) if max_score else 0
    lines = [f"✅ {who} «{esc(short(title, 60))}» vazifasi tekshirildi va baholandi.",
             f"🎯 Olingan baho: <b>{num(score)}/{num(max_score)}</b> ({pct}%)"]
    if comment:
        lines.append(f"💬 Mentor: {esc(short(comment, 300))}")
    lines += ["", esc(motivation_text or motivation(score, max_score, for_parent, salt=int(score)))]
    return "\n".join(lines)


def render_new_homework(student_name: str, title: str, due_at, max_score: float, group_name: str,
                        for_parent: bool, kind: str = "homework") -> str:
    what = "uyga vazifa" if kind == "homework" else "qo'shimcha topshiriq"
    who = f"Farzandingiz <b>{esc(student_name)}</b> uchun" if for_parent else f"<b>{esc(student_name)}</b>, sizga"
    lines = [f"📚 {who} yangi {what} berildi!", f"📌 «{esc(short(title, 80))}» ({esc(group_name)})",
             f"🎯 Maksimal ball: <b>{num(max_score)}</b>"]
    if due_at:
        lines.append(f"⏰ Muddat: <b>{fmt_dt(due_at)}</b>")
    lines += ["", "Vaqtida topshirsangiz jarima bo'lmaydi. Omad! 💪" if not for_parent
              else "Iltimos, farzandingiz vazifani vaqtida topshirishiga ko'maklashing. 🙏"]
    return "\n".join(lines)
