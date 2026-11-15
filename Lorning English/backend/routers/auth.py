import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, desc, func
from sqlalchemy.orm import Session

from config import settings
from deps import get_db, get_current_user
from messages import AppError, lang_from_request
from models.group import Group, GroupMember
from models.user import User, OTPCode
from schemas.auth import OTPRequest, OTPVerify, RegisterComplete, LoginRequest, StudentRegister, user_out
from security import hash_password, verify_password, create_token, decode_token, hash_code, codes_equal
from services import scoring
from services.email_service import send_otp_email
from services import otp_delivery
from services import roster as roster_service
from utils import utcnow, normalize_identifier

router = APIRouter(prefix="/auth", tags=["auth"])

OTP_TTL_MINUTES = 10
MAX_ATTEMPTS = 5
RESEND_SECONDS = 60
MAX_PER_HOUR = 5


def find_user(db: Session, channel: str, target: str):
    col = User.email if channel == "email" else User.phone
    return db.scalar(select(User).where(col == target))


@router.post("/register/request")
def register_request(data: OTPRequest, request: Request, db: Session = Depends(get_db)):
    lang = lang_from_request(request)
    channel, target = normalize_identifier(data.identifier)
    if find_user(db, channel, target):
        raise AppError(409, "user_exists")

    now = utcnow()
    last = db.scalar(
        select(OTPCode).where(OTPCode.target == target, OTPCode.purpose == "register").order_by(desc(OTPCode.created_at)).limit(1)
    )
    if last:
        passed = (now - last.created_at).total_seconds()
        if passed < RESEND_SECONDS:
            raise AppError(429, "otp_wait", seconds=int(RESEND_SECONDS - passed) + 1)
    sent_last_hour = db.scalar(
        select(func.count()).select_from(OTPCode).where(OTPCode.target == target, OTPCode.created_at > now - timedelta(hours=1))
    )
    if sent_last_hour >= MAX_PER_HOUR:
        raise AppError(429, "otp_rate_limit")

    code = f"{secrets.randbelow(10 ** 6):06d}"
    db.add(OTPCode(channel=channel, target=target, code_hash=hash_code(code), expires_at=now + timedelta(minutes=OTP_TTL_MINUTES)))
    db.commit()

    # Telefon kodini SMS xizmati yoki DEV rejimidagi konsol orqali yuboradi.
    res = send_otp_email(target, code, lang) if channel == "email" else otp_delivery.deliver_phone_otp(target, code, lang)
    if not res["ok"]:
        print(f"[OTP send failed] {res['error']}")
        raise AppError(502, "otp_send_failed")
    return {"sent": True, "channel": channel, "identifier": target, "resend_in": RESEND_SECONDS,
            "expires_in": OTP_TTL_MINUTES * 60, "dev": res["dev"],
            "via": res.get("via", "email" if channel == "email" else "sms"),
            # Faqat DEV rejimida (email yoki SMS sozlanmagan): kod avtomatik terib beriladi
            "dev_code": code if res["dev"] else None}


@router.post("/register/verify")
def register_verify(data: OTPVerify, db: Session = Depends(get_db)):
    channel, target = normalize_identifier(data.identifier)
    otp = db.scalar(
        select(OTPCode)
        .where(OTPCode.target == target, OTPCode.purpose == "register", OTPCode.consumed.is_(False))
        .order_by(desc(OTPCode.created_at)).limit(1)
    )
    if not otp:
        raise AppError(400, "otp_not_found")
    if otp.attempts >= MAX_ATTEMPTS:
        raise AppError(429, "otp_locked")
    if utcnow() > otp.expires_at:
        raise AppError(400, "otp_expired")
    if not codes_equal(hash_code(data.code), otp.code_hash):
        otp.attempts += 1
        db.commit()
        raise AppError(400, "otp_invalid", left=max(0, MAX_ATTEMPTS - otp.attempts))
    otp.verified = True
    db.commit()
    token = create_token(target, typ="register", minutes=30, ch=channel)
    return {"registration_token": token}


@router.post("/register/complete")
def register_complete(data: RegisterComplete, request: Request, db: Session = Depends(get_db)):
    payload = decode_token(data.registration_token)
    if not payload or payload.get("typ") != "register":
        raise AppError(400, "reg_token_invalid")
    channel, target = payload.get("ch"), payload.get("sub")
    if channel not in ("email", "phone") or not target:
        raise AppError(400, "reg_token_invalid")

    otp = db.scalar(
        select(OTPCode)
        .where(OTPCode.target == target, OTPCode.purpose == "register", OTPCode.verified.is_(True), OTPCode.consumed.is_(False))
        .order_by(desc(OTPCode.created_at)).limit(1)
    )
    if not otp:
        raise AppError(400, "reg_token_invalid")
    if find_user(db, channel, target):
        raise AppError(409, "user_exists")

    now = utcnow()
    user = User(
        name=data.name.strip(),
        email=target if channel == "email" else None,
        phone=target if channel == "phone" else None,
        password_hash=hash_password(data.password),
        language=lang_from_request(request),
        last_login_at=now, last_seen_at=now,
    )
    user.claimed = True
    user.student_profile.claimed_at = now
    db.add(user)
    otp.consumed = True
    db.commit()
    return {"access_token": create_token(user.id), "token_type": "bearer", "user": user_out(user)}


@router.get("/config")
def auth_config():
    return {"require_otp": settings.REQUIRE_OTP}


@router.post("/register/student")
def register_student(data: StudentRegister, request: Request, db: Session = Depends(get_db)):
    """O'quvchi: guruh -> ism-familiya -> telefon/email + parol. O'quvchi avtomatik shu guruhning jadvaliga tushadi."""
    group = db.get(Group, data.group_id)
    if not group:
        raise AppError(404, "group_not_found")
    name = roster_service.clean_name(data.name)
    if len(name) < 2:
        raise AppError(400, "name_invalid")
    otp = None
    if settings.REQUIRE_OTP:
        payload = decode_token(data.registration_token or "")
        if not payload or payload.get("typ") != "register":
            raise AppError(400, "reg_token_invalid")
        channel, target = payload.get("ch"), payload.get("sub")
        otp = db.scalar(select(OTPCode).where(OTPCode.target == target, OTPCode.purpose == "register", OTPCode.verified.is_(True),
                                              OTPCode.consumed.is_(False)).order_by(desc(OTPCode.created_at)).limit(1))
        if channel not in ("email", "phone") or not otp:
            raise AppError(400, "reg_token_invalid")
    else:
        channel, target = normalize_identifier(data.identifier or "")
    if find_user(db, channel, target):
        raise AppError(409, "user_exists")
    now = utcnow()
    # O'qituvchi shu ismni jadvalga oldindan kiritgan bo'lsa, o'sha yozuv (baho/davomat bilan) hisobga aylanadi
    ph = db.scalar(select(User).join(GroupMember, GroupMember.student_id == User.id)
                   .where(GroupMember.group_id == group.id, User.role == "student",
                          func.lower(User.name) == name.lower()).limit(1))
    if ph is not None and ph.claimed:
        ph = None
    if ph is None:
        ph = User(name=name, password_hash="!", role="student", track=group.kind, onboarded=True, claimed=False)
        db.add(ph)
        db.flush()
        db.add(GroupMember(group_id=group.id, student_id=ph.id))
    if channel == "email":
        ph.email = target
    else:
        ph.phone = target
    ph.password_hash = hash_password(data.password)
    ph.claimed, ph.onboarded, ph.is_active = True, True, True
    ph.student_profile.claimed_at = utcnow()
    ph.language = lang_from_request(request)
    ph.last_login_at = ph.last_seen_at = now
    if otp:
        otp.consumed = True
    db.commit()
    return {"access_token": create_token(ph.id), "token_type": "bearer", "user": user_out(ph)}


@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    try:
        channel, target = normalize_identifier(data.identifier)
    except AppError:
        raise AppError(401, "invalid_credentials")
    user = find_user(db, channel, target)
    if not user or user.role not in ("student", "teacher") or not verify_password(data.password, user.password_hash):
        raise AppError(401, "invalid_credentials")
    if not user.is_active:
        raise AppError(403, "account_blocked")
    now = utcnow()
    user.last_login_at = now
    user.last_seen_at = now
    if user.role == "student":
        scoring.recalculate(db, user.id)
    db.commit()
    return {"access_token": create_token(user.id), "token_type": "bearer", "user": user_out(user)}


@router.get("/me")
def me(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == "student":
        scoring.recalculate(db, user.id)
    db.commit()
    return user_out(user)
