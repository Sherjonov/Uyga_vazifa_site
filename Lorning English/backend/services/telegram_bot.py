"""Learning English Telegram boti: ota-onalar va o'quvchilar uchun (long polling, backend ichida alohida oqimda).

Ota-ona:   /ota_ona -> guruh -> farzand ismi -> tasdiqlash. So'ng /farzandim_statusi, /farzandim_reytingi ...
O'quvchi:  /oquvchi -> raqamni ulashish -> guruh -> ism -> parol. Saytga shu raqam va parol bilan kiradi.
Sayt:      telefon raqam yozilsa tasdiqlash kodi shu botdan olinadi (services/otp_delivery.py).
O'qituvchi saytdan tanlangan ota-onaga xabar yozsa, u shu botdagi profiliga tushadi (services/notifier.py)."""
import os
import re
import threading
import time
import traceback
from typing import Callable, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
from messages import AppError
from models.assignment import Assignment, Submission
from models.group import Group, GroupMember
from models.message import DirectMessage
from models.telegram import ParentLink, TelegramAccount
from models.user import ParentContact, User
from security import decode_token, hash_password
from services import bot_texts, child_stats, otp_delivery
from services import scoring
from services import telegram_api as tg
from services.telegram_api import TelegramError, esc
from utils import normalize_phone, utcnow

PAGE = 8
MAX_CHILDREN = 5          # bitta Telegram akkauntga ko'pi bilan nechta farzand
MAX_PARENTS_PER_CHILD = 4  # bitta farzandga ko'pi bilan nechta ota-ona

CMD_START = [("start", "Boshlash"), ("ota_ona", "Ota-ona: farzandni ulash"),
             ("oquvchi", "O'quvchi: ro'yxatdan o'tish"), ("yordam", "Yordam")]
CMD_PARENT = [("farzandim_bilim_darajasi", "Farzandimning bilim darajasi"), ("status", "Holat: vazifa, lug'at, testlar"),
              ("reyting", "Reytingdagi o'rni"), ("oqituvchiga_xabar", "O'qituvchiga xabar yuborish"),
              ("farzandim_vazifalari", "Uyga vazifa va ballar"), ("farzandim_testlari", "Test natijalari"),
              ("farzandim_davomati", "Davomat"), ("farzandlarim", "Farzandlarim"),
              ("ota_ona", "Yana farzand qo'shish"), ("yordam", "Yordam")]
CMD_STUDENT = [("status", "Holatim: vazifa, lug'at, testlar"), ("vazifalarim", "Vazifalarim holati"), ("natijam", "Mening natijam"),
               ("reyting", "Reytingdagi o'rnim"), ("topshirish", "Uy vazifasini topshirish"), ("yordam", "Yordam")]

REPORTS = {
    "st": bot_texts.render_status, "rk": bot_texts.render_rank, "hw": bot_texts.render_homework,
    "ts": bot_texts.render_tests, "at": bot_texts.render_attendance, "lv": bot_texts.render_level,
}
# buyruq -> hisobot kodi
PARENT_CMDS = {"farzandim_statusi": "st", "farzandim_reytingi": "rk", "farzandim_vazifalari": "hw",
               "farzandim_testlari": "ts", "farzandim_davomati": "at",
               "farzandim_bilim_darajasi": "lv", "farzandim_bilim_daraja": "lv", "bilim_darajasi": "lv"}
STUDENT_CMDS = {"natijam": "st", "vazifalarim": "hw"}
# Ota-ona ham, o'quvchi ham ishlata oladigan buyruqlar: ota-onada farzandi, o'quvchida o'zi ko'rsatiladi
SHARED_CMDS = {"status": "st", "reyting": "rk"}


def site_url() -> str:
    return (settings.PUBLIC_URL or settings.FRONTEND_URL).rstrip("/")


# ───────────────────────── yordamchilar ─────────────────────────

class Ctx:
    def __init__(self, db: Session, acc: TelegramAccount, message_id: Optional[int] = None, callback_id: Optional[str] = None):
        self.db, self.acc, self.message_id, self.callback_id = db, acc, message_id, callback_id

    @property
    def chat_id(self) -> int:
        return self.acc.chat_id


def kb(rows: List[List[Tuple[str, str]]]) -> dict:
    return {"inline_keyboard": [[{"text": t, "callback_data": d} for t, d in row] for row in rows]}


CONTACT_KB = {"keyboard": [[{"text": "📱 Raqamni ulashish", "request_contact": True}]],
              "resize_keyboard": True, "one_time_keyboard": True}
REMOVE_KB = {"remove_keyboard": True}


def send(ctx: Ctx, text: str, markup: Optional[dict] = None) -> None:
    try:
        tg.send_message(ctx.chat_id, text, markup)
    except TelegramError as e:
        if e.blocked:
            ctx.acc.blocked = True
        print(f"[telegram] send failed: {e}")


def show(ctx: Ctx, text: str, markup: Optional[dict] = None) -> None:
    """Tugma bosilganda xabarni joyida yangilaydi, aks holda yangi xabar yuboradi."""
    if ctx.message_id:
        try:
            tg.edit_message(ctx.chat_id, ctx.message_id, text, markup)
            return
        except TelegramError as e:
            if "not modified" in str(e).lower():
                return
    send(ctx, text, markup)


def pages(total: int) -> int:
    return max(1, (total + PAGE - 1) // PAGE)


def nav(prefix: str, page: int, total: int) -> List[Tuple[str, str]]:
    n = pages(total)
    row = []
    if page > 0:
        row.append(("◀️ Oldingi", f"{prefix}:{page - 1}"))
    if page < n - 1:
        row.append(("Keyingi ▶️", f"{prefix}:{page + 1}"))
    return row


def clean_phone(raw: str) -> Optional[str]:
    try:
        return normalize_phone(raw)
    except AppError:
        digits = re.sub(r"\D", "", raw or "")
        return "+" + digits if 8 <= len(digits) <= 15 else None


# ───────────────────────── akkaunt va rollar ─────────────────────────

def get_account(db: Session, tg_user: dict) -> TelegramAccount:
    uid = int(tg_user["id"])
    full = " ".join(p for p in (tg_user.get("first_name"), tg_user.get("last_name")) if p)[:160]
    acc = db.scalar(select(TelegramAccount).where(TelegramAccount.chat_id == uid))
    if not acc:
        acc = TelegramAccount(chat_id=uid, username=tg_user.get("username"), full_name=full, state_data={})
        db.add(acc)
        db.flush()
    else:
        acc.username = tg_user.get("username") or acc.username
        acc.full_name = full or acc.full_name
        acc.blocked = False
    return acc


def set_state(acc: TelegramAccount, state: Optional[str], data: Optional[dict] = None) -> None:
    acc.state = state
    acc.state_data = data or {}


def own_student(db: Session, acc: TelegramAccount) -> Optional[User]:
    """Shu Telegram akkauntga ulangan o'quvchi hisobi. Telefon bo'yicha avtomatik ulanadi."""
    if acc.user_id:
        u = db.get(User, acc.user_id)
        if u and u.role == "student":
            return u
        acc.user_id = None
    if acc.phone:
        u = db.scalar(select(User).where(User.phone == acc.phone, User.role == "student"))
        if u and u.claimed:
            attach_student(db, acc, u)
            return u
    return None


def attach_student(db: Session, acc: TelegramAccount, user: User) -> None:
    for other in db.scalars(select(TelegramAccount).where(TelegramAccount.user_id == user.id, TelegramAccount.id != acc.id)).all():
        other.user_id = None
    acc.user_id = user.id


def children(db: Session, acc: TelegramAccount) -> List[User]:
    return list(db.scalars(
        select(User).join(ParentLink, ParentLink.student_id == User.id)
        .where(ParentLink.telegram_account_id == acc.id).order_by(User.name)
    ).all())


def refresh_commands(ctx: Ctx) -> None:
    """Rolga qarab chatdagi buyruqlar menyusini yangilaydi."""
    cmds: List[Tuple[str, str]] = []
    if children(ctx.db, ctx.acc):
        cmds += CMD_PARENT
    if own_student(ctx.db, ctx.acc):
        cmds += [c for c in CMD_STUDENT if c not in cmds]
    if not cmds:
        cmds = CMD_START
    seen, out = set(), []
    for c, d in cmds:
        if c not in seen:
            seen.add(c)
            out.append({"command": c, "description": d})
    tg.set_commands(out, ctx.chat_id)


# ───────────────────────── asosiy buyruqlar ─────────────────────────

def welcome(ctx: Ctx) -> None:
    acc, db = ctx.acc, ctx.db
    kids, me = children(db, acc), own_student(db, acc)
    name = esc(acc.full_name or "do'stim")
    lines = [f"Assalomu alaykum, <b>{name}</b>! 👋", "Learning English o'quv platformasi botiga xush kelibsiz.", ""]
    if me:
        lines.append(f"🎓 O'quvchi hisobi: <b>{esc(me.name)}</b> — /vazifalarim, /natijam, /reyting")
    if kids:
        lines.append("👨‍👩‍👧 Farzandlaringiz: " + ", ".join(f"<b>{esc(k.name)}</b>" for k in kids))
        lines.append("/farzandim_bilim_darajasi · /status · /reyting · /oqituvchiga_xabar")
    if not me and not kids:
        lines += ["👨‍👩‍👧 <b>Ota-ona</b> bo'lsangiz — farzandingizning o'rni, vazifalari va test natijalarini shu yerda kuzating: /ota_ona",
                  "🎓 <b>O'quvchi</b> bo'lsangiz — ro'yxatdan o'ting yoki hisobingizni ulang: /oquvchi"]
    lines += ["", "Barcha buyruqlar: /yordam"]
    rows = []
    if not kids:
        rows.append([("👨‍👩‍👧 Men ota-onaman", "m:p")])
    if not me:
        rows.append([("🎓 Men o'quvchiman", "m:s")])
    send(ctx, "\n".join(lines), kb(rows) if rows else None)


def cmd_help(ctx: Ctx) -> None:
    send(ctx, (
        "<b>📖 Yordam</b>\n\n"
        "<b>Ota-onalar uchun</b>\n"
        "/ota_ona — farzandni ulash (guruh → ism)\n"
        "/farzandim_bilim_darajasi — farzandimning bilim darajasi\n"
        "/status — bajargan vazifalar (10/15), lug'at va testlar\n"
        "/reyting — guruh va umumiy reytingdagi o'rni\n"
        "/oqituvchiga_xabar — o'qituvchiga xabar yuborish\n"
        "/farzandim_vazifalari — uyga vazifa va olingan ballar\n"
        "/farzandim_testlari — test natijalari (%)\n"
        "/farzandim_davomati — davomat\n"
        "/farzandlarim — farzandlar ro'yxati\n"
        "<i>Davomat, topshirilmagan vazifa, vazifa bahosi va xavf zonasi haqida xabarlar avtomatik keladi.</i>\n\n"
        "<b>O'quvchilar uchun</b>\n"
        "/oquvchi — ro'yxatdan o'tish yoki saytdagi hisobni ulash\n"
        "/vazifalarim — vazifalarim holati\n"
        "/topshirish — uy vazifasini matn ko'rinishida topshirish\n"
        "/natijam — mening statistikam\n"
        "/reyting — reytingdagi o'rnim\n\n"
        f"🌐 Sayt: {esc(site_url())}\n/bekor — joriy amalni bekor qilish"))


def cmd_start(ctx: Ctx, arg: str) -> None:
    set_state(ctx.acc, None)
    if arg.startswith("link_"):
        return link_with_token(ctx, arg[5:])
    if arg == "otp" and not ctx.acc.phone:
        set_state(ctx.acc, "contact_otp")
        return send(ctx, "🔐 <b>Saytda ro'yxatdan o'tish uchun kod</b>\n\nPastdagi <b>«📱 Raqamni ulashish»</b> tugmasini bosing — "
                         "kod shu yerda keladi.", CONTACT_KB)
    if not ctx.acc.phone:
        return ask_contact(
            ctx, "otp",
            "Ro'yxatdan o'tishda kiritgan telefon raqamingizni shu tugma orqali ulashing. "
            "Raqam avtomatik aniqlanmaydi; Telegram faqat siz tasdiqlagan kontaktni beradi. "
            "Agar saytda kod so'ragan bo'lsangiz, kod shu chatga yuboriladi.",
        )
    if ctx.acc.phone:  # raqam oldin ulangan bo'lsa, kutilayotgan kodni darhol beramiz
        code = otp_delivery.issue_pending_otp(ctx.db, ctx.acc.phone)
        if code:
            send(ctx, otp_delivery.otp_message(code) + "\n\nKodni saytdagi oynaga kiriting.")
    welcome(ctx)
    refresh_commands(ctx)


def link_with_token(ctx: Ctx, token: str) -> None:
    payload = decode_token(token)
    user = None
    if payload and payload.get("typ") == "tglink":
        try:
            user = ctx.db.get(User, int(payload["sub"]))
        except (ValueError, KeyError):
            user = None
    if not user or user.role != "student":
        return send(ctx, "❌ Havola eskirgan yoki noto'g'ri. Saytdan yangi havola oling (Sozlamalar → Telegram).")
    attach_student(ctx.db, ctx.acc, user)
    send(ctx, f"✅ Hisobingiz ulandi: <b>{esc(user.name)}</b>\n\n/vazifalarim · /natijam · /reyting")
    refresh_commands(ctx)


def ask_contact(ctx: Ctx, flow: str, why: str) -> None:
    set_state(ctx.acc, f"contact_{flow}")
    send(ctx, f"📱 {why}\n\nPastdagi <b>«Raqamni ulashish»</b> tugmasini bosing (faqat o'zingizning raqamingiz qabul qilinadi).", CONTACT_KB)


def on_contact(ctx: Ctx, contact: dict, from_id: int) -> None:
    if int(contact.get("user_id") or 0) != int(from_id):
        return send(ctx, "⚠️ Faqat o'zingizning raqamingizni ulashing (tugma orqali).", CONTACT_KB)
    phone = clean_phone(contact.get("phone_number", ""))
    if not phone:
        return send(ctx, "⚠️ Telefon raqamni o'qib bo'lmadi.", CONTACT_KB)
    acc, db = ctx.acc, ctx.db
    acc.phone = phone
    state = acc.state or ""
    set_state(acc, None)
    send(ctx, f"✅ Raqamingiz qabul qilindi: <b>{esc(phone)}</b>", REMOVE_KB)

    code = otp_delivery.issue_pending_otp(db, phone)
    if code:
        send(ctx, otp_delivery.otp_message(code) + "\n\n🌐 Saytga qaytib, shu kodni kiriting.")
    me = own_student(db, acc)
    if me:
        send(ctx, f"🔗 Saytdagi hisobingiz ulandi: <b>{esc(me.name)}</b>\n/vazifalarim · /natijam · /reyting")

    if state == "contact_parent":
        return show_groups(ctx, "p", 0)
    if state == "contact_student":
        return start_student_flow(ctx) if not me else refresh_commands(ctx)
    if not code and not me:
        welcome(ctx)
    refresh_commands(ctx)


# ───────────────────────── guruh va ism tanlash (ota-ona / o'quvchi) ─────────────────────────

def show_groups(ctx: Ctx, mode: str, page: int) -> None:
    """mode: p (ota-ona: barcha guruhlar) | s (o'quvchi: ro'yxatdan o'tmagan ismlari bor guruhlar)."""
    db = ctx.db
    stmt = select(Group.id, Group.name, func.count(GroupMember.id)).join(GroupMember, GroupMember.group_id == Group.id)
    if mode == "s":
        stmt = stmt.join(User, User.id == GroupMember.student_id).where(User.claimed.is_(False))
    rows = db.execute(stmt.group_by(Group.id, Group.name).order_by(Group.name)).all()
    title = "👨‍👩‍👧 <b>Ota-ona sifatida ulanish</b>\nFarzandingiz o'qiydigan guruhni tanlang:" if mode == "p" else \
            "🎓 <b>O'quvchi sifatida ro'yxatdan o'tish</b>\nGuruhingizni tanlang:"
    if not rows:
        return show(ctx, title + "\n\n😕 Hozircha tanlash uchun guruh yo'q. O'qituvchingiz o'quvchilar ismini sayt orqali kiritganini tekshiring.")
    page = min(max(page, 0), pages(len(rows)) - 1)
    chunk = rows[page * PAGE:(page + 1) * PAGE]
    word = "o'quvchi" if mode == "p" else "bo'sh ism"
    buttons = [[(f"{name} · {cnt} {word}", f"gs:{mode}:{gid}:0")] for gid, name, cnt in chunk]
    n = nav(f"gl:{mode}", page, len(rows))
    if n:
        buttons.append(n)
    show(ctx, title, kb(buttons))


def group_names(db: Session, mode: str, gid: int) -> List[Tuple[int, str, bool]]:
    stmt = (select(User.id, User.name, User.claimed).join(GroupMember, GroupMember.student_id == User.id)
            .where(GroupMember.group_id == gid, User.role == "student", User.is_active.is_(True)).order_by(User.name))
    if mode == "s":
        stmt = stmt.where(User.claimed.is_(False))
    return [(i, n, bool(c)) for i, n, c in db.execute(stmt).all()]


def show_names(ctx: Ctx, mode: str, gid: int, page: int) -> None:
    db = ctx.db
    group = db.get(Group, gid)
    if not group:
        return show(ctx, "❌ Guruh topilmadi.", kb([[("⬅️ Guruhlar", f"gl:{mode}:0")]]))
    names = group_names(db, mode, gid)
    linked = set(db.scalars(select(ParentLink.student_id).where(ParentLink.telegram_account_id == ctx.acc.id)).all()) if mode == "p" else set()
    head = f"👥 <b>{esc(group.name)}</b>\n" + ("Farzandingiz ismini tanlang:" if mode == "p" else "Ismingizni tanlang:")
    if not names:
        return show(ctx, head + "\n\n😕 Bu guruhda tanlash uchun ism yo'q.", kb([[("⬅️ Guruhlar", f"gl:{mode}:0")]]))
    page = min(max(page, 0), pages(len(names)) - 1)
    chunk = names[page * PAGE:(page + 1) * PAGE]
    buttons = [[(("✅ " if sid in linked else "") + name, f"ns:{mode}:{sid}:{gid}")] for sid, name, _ in chunk]
    n = nav(f"gs:{mode}:{gid}", page, len(names))
    if n:
        buttons.append(n)
    buttons.append([("⬅️ Guruhlar", f"gl:{mode}:0")])
    show(ctx, head + f"\n<i>Jami: {len(names)} ta</i>", kb(buttons))


def picked_name(ctx: Ctx, mode: str, sid: int, gid: int) -> None:
    db = ctx.db
    student = db.get(User, sid)
    group = db.get(Group, gid)
    if not student or student.role != "student" or not group:
        return show(ctx, "❌ Topilmadi.", kb([[("⬅️ Guruhlar", f"gl:{mode}:0")]]))
    if mode == "p":
        return show(ctx, f"Siz <b>{esc(student.name)}</b> ({esc(group.name)}) ning ota-onasi (yoki vasiysi)misiz?",
                    kb([[("✅ Ha, bu mening farzandim", f"pc:{sid}")], [("⬅️ Orqaga", f"gs:p:{gid}:0")]]))
    if student.claimed:
        return show(ctx, "⚠️ Bu ism allaqachon band qilingan.", kb([[("⬅️ Orqaga", f"gs:s:{gid}:0")]]))
    set_state(ctx.acc, "await_password", {"sid": sid})
    show(ctx, f"🎓 <b>{esc(student.name)}</b> ({esc(group.name)})\n\nSaytga kirish uchun <b>parol o'ylab toping</b> va shu yerga yozing "
              "(kamida 6 belgi).\n🔒 Xavfsizlik uchun xabaringiz yozilgach darhol o'chiriladi.\n\nBekor qilish: /bekor")


def link_parent(ctx: Ctx, sid: int) -> None:
    db, acc = ctx.db, ctx.acc
    student = db.get(User, sid)
    if not student or student.role != "student":
        return show(ctx, "❌ O'quvchi topilmadi.")
    if db.scalar(select(ParentLink.id).where(ParentLink.telegram_account_id == acc.id, ParentLink.student_id == sid)):
        return show(ctx, f"ℹ️ <b>{esc(student.name)}</b> allaqachon ulangan: /farzandim_statusi")
    if len(children(db, acc)) >= MAX_CHILDREN:
        return show(ctx, f"⚠️ Bitta akkauntga ko'pi bilan {MAX_CHILDREN} ta farzand ulash mumkin.")
    if (db.scalar(select(func.count()).select_from(ParentLink).where(ParentLink.student_id == sid)) or 0) >= MAX_PARENTS_PER_CHILD:
        return show(ctx, f"⚠️ Bu o'quvchiga allaqachon {MAX_PARENTS_PER_CHILD} ta ota-ona ulangan. O'qituvchi bilan bog'laning.")
    db.add(ParentLink(telegram_account_id=acc.id, student_id=sid))
    acc.active_student_id = sid
    # O'qituvchi sahifasida kontakt ko'rinishi uchun (mavjud ma'lumot ustidan yozilmaydi)
    contact = db.scalar(select(ParentContact).where(ParentContact.student_id == sid))
    if not contact:
        contact = ParentContact(student_id=sid)
        db.add(contact)
    if not contact.parent_name:
        contact.parent_name = acc.full_name or None
    if not contact.phone and acc.phone and re.fullmatch(r"\+998\d{9}", acc.phone):
        contact.phone = acc.phone
    db.flush()
    show(ctx, f"✅ <b>{esc(student.name)}</b> farzandingiz sifatida ulandi!\n\nEndi quyidagilarni ko'rishingiz mumkin:",
         kb([[("🎓 Bilim darajasi", f"cp:lv:{sid}"), ("📊 Holati", f"cp:st:{sid}")],
             [("🏆 Reyting", f"cp:rk:{sid}"), ("🏠 Vazifalar", f"cp:hw:{sid}")],
             [("📝 Testlar", f"cp:ts:{sid}"), ("📅 Davomat", f"cp:at:{sid}")]]))
    send(ctx, "Davomat, topshirilmagan vazifa, vazifa bahosi va xavf zonasi haqida xabarlar shu yerga avtomatik keladi. "
              "O'qituvchiga yozish: /oqituvchiga_xabar 👨‍🏫")
    refresh_commands(ctx)


def cmd_parent(ctx: Ctx) -> None:
    set_state(ctx.acc, None)
    if not ctx.acc.phone:
        return ask_contact(ctx, "parent", "Ota-ona sifatida ulanish uchun avval telefon raqamingizni ulashing.")
    show_groups(ctx, "p", 0)


def start_student_flow(ctx: Ctx) -> None:
    show_groups(ctx, "s", 0)


def cmd_student(ctx: Ctx) -> None:
    set_state(ctx.acc, None)
    me = own_student(ctx.db, ctx.acc)
    if me:
        return send(ctx, f"✅ Siz allaqachon ulangansiz: <b>{esc(me.name)}</b>\n\n/vazifalarim · /natijam · /reyting")
    if not ctx.acc.phone:
        return ask_contact(ctx, "student", "Ro'yxatdan o'tish uchun telefon raqamingizni ulashing. Saytga shu raqam bilan kirasiz.")
    start_student_flow(ctx)


def finish_registration(ctx: Ctx, password: str, user_msg_id: Optional[int]) -> None:
    db, acc = ctx.db, ctx.acc
    if user_msg_id:
        tg.delete_message(ctx.chat_id, user_msg_id)  # parol chatda qolmasin
    if not 6 <= len(password) <= 72:
        return send(ctx, "⚠️ Parol 6 dan 72 tagacha belgi bo'lishi kerak. Qayta yozing (bekor qilish: /bekor).")
    sid = (acc.state_data or {}).get("sid")
    ph = db.get(User, sid) if sid else None
    if not ph or ph.role != "student" or ph.claimed:
        set_state(acc, None)
        return send(ctx, "⚠️ Bu ism band bo'lib qolibdi yoki topilmadi. Qayta boshlang: /oquvchi")
    if not acc.phone or not re.fullmatch(r"\+998\d{9}", acc.phone):
        set_state(acc, None)
        return send(ctx, "⚠️ Ro'yxatdan o'tish uchun O'zbekiston raqami (+998) kerak.")
    taken = db.scalar(select(User).where(User.phone == acc.phone, User.id != ph.id))
    if taken:
        set_state(acc, None)
        if taken.role == "student" and taken.claimed:
            attach_student(db, acc, taken)
            refresh_commands(ctx)
            return send(ctx, f"ℹ️ Bu raqam saytda ro'yxatdan o'tgan, hisob ulandi: <b>{esc(taken.name)}</b>\n/vazifalarim · /natijam")
        return send(ctx, "⚠️ Bu raqam boshqa hisobga biriktirilgan. O'qituvchiga murojaat qiling.")
    ph.phone = acc.phone
    ph.password_hash = hash_password(password)
    ph.claimed, ph.onboarded, ph.is_active, ph.language = True, True, True, "uz"
    ph.student_profile.claimed_at = utcnow()
    ph.last_login_at = ph.last_seen_at = utcnow()
    attach_student(db, acc, ph)
    set_state(acc, None)
    db.flush()
    send(ctx, f"🎉 <b>Ro'yxatdan o'tdingiz, {esc(ph.name)}!</b>\n\n🌐 Sayt: {esc(site_url())}/login\n"
              f"📞 Login: <code>{esc(acc.phone)}</code>\n🔑 Parol: siz yozgan parol\n\n"
              "Bu yerda ham: /vazifalarim · /natijam · /reyting")
    refresh_commands(ctx)


def cmd_submit_homework(ctx: Ctx) -> None:
    student = own_student(ctx.db, ctx.acc)
    if not student:
        return send(ctx, "ℹ️ Avval o'quvchi sifatida hisobingizni ulang: /oquvchi")
    group_ids = list(ctx.db.scalars(
        select(GroupMember.group_id).where(GroupMember.student_id == student.id)
    ).all())
    now = utcnow()
    assignments = ctx.db.scalars(
        select(Assignment).where(
            Assignment.group_id.in_(group_ids or [0]),
            Assignment.kind == "homework",
            (Assignment.due_at.is_(None)) | (Assignment.due_at >= now),
        ).order_by(Assignment.due_at, Assignment.created_at.desc())
    ).all()
    submissions = {
        row.assignment_id: row for row in ctx.db.scalars(
            select(Submission).where(
                Submission.student_id == student.id,
                Submission.assignment_id.in_([item.id for item in assignments] or [0]),
            )
        ).all()
    }
    available = [item for item in assignments if not (submissions.get(item.id) and submissions[item.id].submitted_at)]
    if not available:
        return send(ctx, "✅ Hozir topshirish mumkin bo'lgan uy vazifasi yo'q.")
    rows = [[(item.title[:55], f"as:{item.id}")] for item in available[:50]]
    set_state(ctx.acc, None)
    send(ctx, "Topshirmoqchi bo'lgan uy vazifangizni tanlang:", kb(rows))


def choose_homework(ctx: Ctx, assignment_id: int) -> None:
    student = own_student(ctx.db, ctx.acc)
    assignment = ctx.db.get(Assignment, assignment_id)
    if not student or not assignment or assignment.kind != "homework" or not ctx.db.scalar(
        select(GroupMember.id).where(
            GroupMember.group_id == assignment.group_id, GroupMember.student_id == student.id
        )
    ):
        set_state(ctx.acc, None)
        return send(ctx, "⚠️ Uy vazifasi topilmadi yoki sizga biriktirilmagan. /topshirish")
    if assignment.due_at and assignment.due_at < utcnow():
        set_state(ctx.acc, None)
        return send(ctx, "⏰ Bu uy vazifasining muddati o'tgan.")
    submission = ctx.db.scalar(select(Submission).where(
        Submission.assignment_id == assignment.id, Submission.student_id == student.id
    ))
    if submission and submission.submitted_at:
        set_state(ctx.acc, None)
        return send(ctx, "ℹ️ Bu uy vazifasi allaqachon topshirilgan.")
    set_state(ctx.acc, "await_submission", {"assignment_id": assignment.id})
    send(ctx, f"📝 <b>{esc(assignment.title)}</b>\n\nJavobingizni bitta matnli xabar qilib yuboring "
              "(Telegram orqali hozircha matn qabul qilinadi, 20 000 belgigacha).\nBekor qilish: /bekor")


def finish_homework_submission(ctx: Ctx, text: str) -> None:
    student = own_student(ctx.db, ctx.acc)
    assignment_id = (ctx.acc.state_data or {}).get("assignment_id")
    assignment = ctx.db.get(Assignment, assignment_id) if assignment_id else None
    answer = text.strip()
    if not student or not assignment or assignment.kind != "homework" or not ctx.db.scalar(
        select(GroupMember.id).where(
            GroupMember.group_id == assignment.group_id, GroupMember.student_id == student.id
        )
    ):
        set_state(ctx.acc, None)
        return send(ctx, "⚠️ Uy vazifasi topilmadi. Qaytadan boshlang: /topshirish")
    if not answer:
        return send(ctx, "⚠️ Javob bo'sh bo'lmasin. Javob matnini yuboring yoki /bekor bosing.")
    if len(answer) > 20000:
        return send(ctx, "⚠️ Javob 20 000 belgidan oshmasligi kerak. Qisqartirib qayta yuboring.")
    now = utcnow()
    if assignment.due_at and now > assignment.due_at:
        set_state(ctx.acc, None)
        return send(ctx, "⏰ Uy vazifasining muddati o'tib ketdi; javob yuborilmadi.")
    submission = ctx.db.scalar(select(Submission).where(
        Submission.assignment_id == assignment.id, Submission.student_id == student.id
    ))
    if submission and submission.submitted_at:
        set_state(ctx.acc, None)
        return send(ctx, "ℹ️ Bu uy vazifasi boshqa joydan allaqachon topshirilgan.")
    if not submission:
        submission = Submission(assignment_id=assignment.id, student_id=student.id)
        ctx.db.add(submission)
    submission.text = answer
    submission.submitted_at = now
    scoring.recalculate(ctx.db, student.id)
    set_state(ctx.acc, None)
    send(ctx, f"✅ <b>{esc(assignment.title)}</b> uy vazifasi topshirildi. O'qituvchi tekshirganidan keyin natijani ko'rasiz.")


# ───────────────────────── hisobotlar ─────────────────────────

def allowed_sids(db: Session, acc: TelegramAccount) -> List[int]:
    ids = [c.id for c in children(db, acc)]
    me = own_student(db, acc)
    if me:
        ids.append(me.id)
    return ids


def report_kb(sid: int, current: str, multi: bool) -> dict:
    items = [("lv", "🎓 Bilim darajasi"), ("st", "📊 Holat"), ("rk", "🏆 Reyting"), ("hw", "🏠 Vazifalar"),
             ("ts", "📝 Testlar"), ("at", "📅 Davomat")]
    items = [(t, f"cp:{k}:{sid}") for k, t in items if k != current]
    rows = [items[i:i + 2] for i in range(0, len(items), 2)]
    if multi:
        rows.append([("👥 Farzandlarim", "kids")])
    return kb(rows)


def run_report(ctx: Ctx, code: str, sid: Optional[int], own: bool = False) -> None:
    """code: st|rk|hw|ts|at. sid berilmasa: o'quvchi o'zi (own) yoki yagona farzand; bir nechta bo'lsa so'raydi."""
    db, acc = ctx.db, ctx.acc
    kids = children(db, acc)
    if sid is None:
        if own:
            me = own_student(db, acc)
            if not me:
                return send(ctx, "ℹ️ Avval o'quvchi sifatida ulaning: /oquvchi")
            sid = me.id
        else:
            if not kids:
                return send(ctx, "ℹ️ Hali farzand ulanmagan. Ulash uchun: /ota_ona")
            if len(kids) == 1:
                sid = kids[0].id
            else:
                return send(ctx, "Qaysi farzandingiz haqida?", kb([[(f"👤 {k.name}", f"cp:{code}:{k.id}")] for k in kids]))
    if sid not in allowed_sids(db, acc):
        return show(ctx, "⚠️ Bu o'quvchi sizga ulanmagan.")
    ov = child_stats.overview(db, sid)
    if not ov:
        return show(ctx, "❌ Ma'lumot topilmadi.")
    is_child = sid in [k.id for k in kids]
    if is_child:
        acc.active_student_id = sid
    show(ctx, REPORTS[code](ov), report_kb(sid, code, is_child and len(kids) > 1))


def cmd_children(ctx: Ctx) -> None:
    kids = children(ctx.db, ctx.acc)
    if not kids:
        return show(ctx, "ℹ️ Hali farzand ulanmagan. Ulash uchun: /ota_ona")
    rows = [[(f"👤 {k.name}", f"cp:st:{k.id}"), ("🗑", f"ul:{k.id}")] for k in kids]
    if len(kids) < MAX_CHILDREN:
        rows.append([("➕ Farzand qo'shish", "m:p")])
    show(ctx, "👨‍👩‍👧 <b>Farzandlarim</b>\nStatistikani ko'rish uchun ismni bosing:", kb(rows))


def cmd_teacher_message(ctx: Ctx) -> None:
    """/oqituvchiga_xabar: ota-ona farzandining o'qituvchisiga xabar yozadi."""
    set_state(ctx.acc, None)
    kids = children(ctx.db, ctx.acc)
    if not kids:
        return send(ctx, "ℹ️ Avval farzandingizni ulang: /ota_ona")
    if len(kids) == 1:
        return begin_teacher_message(ctx, kids[0].id)
    send(ctx, "Qaysi farzandingizning o'qituvchisiga xabar yozmoqchisiz?",
         kb([[(f"👤 {k.name}", f"tm:{k.id}")] for k in kids]))


def begin_teacher_message(ctx: Ctx, sid: int) -> None:
    if sid not in [k.id for k in children(ctx.db, ctx.acc)]:
        return show(ctx, "⚠️ Bu o'quvchi sizga ulanmagan.")
    student = ctx.db.get(User, sid)
    set_state(ctx.acc, "await_teacher_msg", {"sid": sid})
    send(ctx, f"✍️ <b>{esc(student.name if student else '')}</b> o'qituvchisiga xabaringizni yozing va yuboring "
              "(1000 belgigacha).\nBekor qilish: /bekor")


def finish_teacher_message(ctx: Ctx, text: str) -> None:
    db, acc = ctx.db, ctx.acc
    sid = (acc.state_data or {}).get("sid")
    body = text.strip()
    if not body:
        return send(ctx, "⚠️ Xabar bo'sh bo'lmasin. Matn yuboring yoki /bekor bosing.")
    if len(body) > 1000:
        return send(ctx, "⚠️ Xabar 1000 belgidan oshmasin. Qisqartirib qayta yuboring.")
    if sid not in [k.id for k in children(db, acc)]:
        set_state(acc, None)
        return send(ctx, "⚠️ Bu o'quvchi sizga ulanmagan: /ota_ona")
    teachers = db.scalars(select(User).join(Group, Group.teacher_id == User.id)
                          .join(GroupMember, GroupMember.group_id == Group.id)
                          .where(GroupMember.student_id == sid).distinct()).all()
    set_state(acc, None)
    if not teachers:
        return send(ctx, "⚠️ Farzandingiz hali guruhga biriktirilmagan, xabarni yuborib bo'lmadi.")
    who = " · ".join(p for p in (acc.full_name, acc.phone) if p) or "Ota-ona"
    for t in teachers:
        # O'qituvchi saytdagi "Xabarlar" bo'limida farzand nomi ostida ko'radi
        db.add(DirectMessage(sender_id=sid, recipient_id=t.id, body=f"👨‍👩‍👧 Ota-ona ({who}) xabari:\n{body}"))
    send(ctx, "✅ Xabaringiz o'qituvchiga yuborildi. Javob saytdagi aloqa orqali yoki o'qituvchi tomonidan shu bot orqali keladi.")


def unlink_ask(ctx: Ctx, sid: int) -> None:
    st = ctx.db.get(User, sid)
    show(ctx, f"<b>{esc(st.name if st else '')}</b> ni ro'yxatingizdan olib tashlaysizmi?",
         kb([[("🗑 Ha, olib tashlash", f"uy:{sid}"), ("Bekor", "kids")]]))


def unlink_do(ctx: Ctx, sid: int) -> None:
    link = ctx.db.scalar(select(ParentLink).where(ParentLink.telegram_account_id == ctx.acc.id, ParentLink.student_id == sid))
    if link:
        ctx.db.delete(link)
        ctx.db.flush()
    refresh_commands(ctx)
    cmd_children(ctx)


# ───────────────────────── yo'naltirish ─────────────────────────

def on_command(ctx: Ctx, cmd: str, arg: str) -> None:
    if cmd == "start":
        return cmd_start(ctx, arg)
    if cmd in ("yordam", "help"):
        return cmd_help(ctx)
    if cmd in ("bekor", "cancel"):
        set_state(ctx.acc, None)
        return send(ctx, "Bekor qilindi.", REMOVE_KB)
    if cmd in ("ota_ona", "otaona"):
        return cmd_parent(ctx)
    if cmd in ("oquvchi", "royxat"):
        return cmd_student(ctx)
    if cmd in ("farzandlarim", "farzand"):
        return cmd_children(ctx)
    if cmd in ("oqituvchiga_xabar", "oqituvchiga"):
        return cmd_teacher_message(ctx)
    if cmd in SHARED_CMDS:
        set_state(ctx.acc, None)
        own = not children(ctx.db, ctx.acc)  # ota-onada farzandi, farzandi bo'lmasa o'quvchining o'zi
        return run_report(ctx, SHARED_CMDS[cmd], None, own=own)
    if cmd in PARENT_CMDS:
        set_state(ctx.acc, None)
        return run_report(ctx, PARENT_CMDS[cmd], None)
    if cmd in STUDENT_CMDS:
        set_state(ctx.acc, None)
        return run_report(ctx, STUDENT_CMDS[cmd], None, own=True)
    if cmd == "topshirish":
        return cmd_submit_homework(ctx)
    send(ctx, "Noma'lum buyruq. Buyruqlar ro'yxati: /yordam")


def on_callback(ctx: Ctx, data: str) -> None:
    p = data.split(":")
    k = p[0]
    try:
        if k == "gl":
            return show_groups(ctx, p[1], int(p[2]))
        if k == "gs":
            return show_names(ctx, p[1], int(p[2]), int(p[3]))
        if k == "ns":
            return picked_name(ctx, p[1], int(p[2]), int(p[3]))
        if k == "pc":
            return link_parent(ctx, int(p[1]))
        if k == "cp" and p[1] in REPORTS:
            return run_report(ctx, p[1], int(p[2]))
        if k == "kids":
            return cmd_children(ctx)
        if k == "ul":
            return unlink_ask(ctx, int(p[1]))
        if k == "uy":
            return unlink_do(ctx, int(p[1]))
        if k == "m":
            return cmd_parent(ctx) if p[1] == "p" else cmd_student(ctx)
        if k == "as":
            return choose_homework(ctx, int(p[1]))
        if k == "tm":
            return begin_teacher_message(ctx, int(p[1]))
    except (IndexError, ValueError):
        pass


def on_text(ctx: Ctx, text: str, msg_id: Optional[int]) -> None:
    if ctx.acc.state == "await_password":
        return finish_registration(ctx, text.strip(), msg_id)
    if ctx.acc.state == "await_submission":
        return finish_homework_submission(ctx, text)
    if ctx.acc.state == "await_teacher_msg":
        return finish_teacher_message(ctx, text)
    send(ctx, "Buyruqlar ro'yxati: /yordam")


def handle_update(update: dict) -> None:
    msg = update.get("message")
    cb = update.get("callback_query")
    src = msg or (cb or {}).get("message")
    if not src or (src.get("chat") or {}).get("type") != "private":
        return
    from_user = (msg or cb).get("from") or {}
    if not from_user.get("id") or from_user.get("is_bot"):
        return
    with SessionLocal() as db:
        acc = get_account(db, from_user)
        ctx = Ctx(db, acc, message_id=src.get("message_id") if cb else None, callback_id=cb.get("id") if cb else None)
        try:
            if cb:
                tg.answer_callback(cb["id"])
                on_callback(ctx, cb.get("data") or "")
            elif msg.get("contact"):
                on_contact(ctx, msg["contact"], from_user["id"])
            elif msg.get("text"):
                text = msg["text"]
                if text.startswith("/"):
                    head, _, arg = text[1:].partition(" ")
                    cmd = head.split("@")[0].lower()
                    on_command(ctx, cmd, arg.strip())
                else:
                    on_text(ctx, text, msg.get("message_id"))
            db.commit()
        except Exception:  # noqa: BLE001 — bitta xato butun botni to'xtatmasin
            db.rollback()
            traceback.print_exc()
            try:
                tg.send_message(acc.chat_id, "⚠️ Kutilmagan xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring.")
            except TelegramError:
                pass


# ───────────────────────── polling ─────────────────────────

_lock_file = None


def owns_lock() -> bool:
    return _lock_file is not None


def _try_lock() -> bool:
    """Shu kompyuterda botni faqat bitta jarayon ushlab turishi uchun fayl qulfi: ikkinchi `python main.py`
    (yoki eski qolib ketgan jarayon) Telegramda 409 Conflict keltirib chiqarmasin. Jarayon tugasa qulf o'zi ochiladi."""
    global _lock_file
    if _lock_file is not None:
        return True
    f = open(settings.UPLOAD_DIR.parent / ".telegram_bot.lock", "a+")
    try:
        if os.name == "nt":
            import msvcrt
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return False
    _lock_file = f
    return True


class _Runner:
    def __init__(self) -> None:
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

    def start(self) -> bool:
        if not tg.is_configured() or not settings.TELEGRAM_POLLING:
            return False
        if self.thread and self.thread.is_alive():
            return True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._loop, name="telegram-bot", daemon=True)
        self.thread.start()
        return True

    def stop(self) -> None:
        self.stop_event.set()

    def _loop(self) -> None:
        told = False
        while not _try_lock():  # boshqa nusxa botni ushlab turibdi (yoki eski jarayon hali yopilmagan): kutamiz
            if not told:
                print("[telegram] Bot boshqa jarayonda ishlayapti; u yopilguncha kutilmoqda (409 to'qnashuvi oldini olish).")
                told = True
            if self.stop_event.wait(3):
                return
        try:
            me = tg.get_me()
        except TelegramError as e:
            print(f"[telegram] Bot ishga tushmadi (TELEGRAM_BOT_TOKEN ni tekshiring): {e}")
            return
        print(f"[telegram] @{me.get('username')} ishga tushdi: https://t.me/{me.get('username')}")
        try:
            tg.call("deleteWebhook")
        except TelegramError:
            pass
        tg.set_commands([{"command": c, "description": d} for c, d in CMD_START])
        offset: Optional[int] = None
        delay = 1.0
        while not self.stop_event.is_set():
            try:
                params = {"timeout": 25, "allowed_updates": ["message", "callback_query"]}
                if offset is not None:
                    params["offset"] = offset
                updates = tg.call("getUpdates", http_timeout=40, **params)
                delay = 1.0
                for u in updates:
                    offset = u["update_id"] + 1
                    handle_update(u)
            except TelegramError as e:
                if e.code == 409:
                    print("[telegram] Boshqa nusxa getUpdates qilyapti (409). Faqat bitta server ishlashi kerak.")
                    delay = 5.0
                elif e.code == 401:
                    print("[telegram] Token noto'g'ri (401). Bot to'xtatildi.")
                    return
                else:
                    print(f"[telegram] polling xatosi: {e}")
                self.stop_event.wait(delay)
                delay = min(delay * 2, 30)
            except Exception:  # noqa: BLE001
                traceback.print_exc()
                self.stop_event.wait(3)


runner = _Runner()


def start() -> bool:
    return runner.start()


def stop() -> None:
    runner.stop()
