import httpx

from config import settings

SUBJECTS = {"uz": "Learning English tasdiqlash kodi", "en": "Learning English verification code", "ru": "Код подтверждения Learning English"}
TEXTS = {
    "uz": "Sizning tasdiqlash kodingiz. Kod 10 daqiqa amal qiladi.",
    "en": "Your verification code. It is valid for 10 minutes.",
    "ru": "Ваш код подтверждения. Действует 10 минут.",
}


def send_email(to: str, subject: str, html: str) -> dict:
    """-> {"ok": bool, "dev": bool, "error": str|None}. Kalit yo'q bo'lsa DEV rejimi."""
    if not settings.RESEND_API_KEY:
        print(f"\n[DEV EMAIL] to={to}\nsubject={subject}\n{html}\n")
        return {"ok": True, "dev": True, "error": None}
    sender = settings.RESEND_FROM_EMAIL or "Learning English <onboarding@resend.dev>"
    try:
        r = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
            json={"from": sender, "to": [to], "subject": subject, "html": html},
            timeout=15,
        )
        if r.status_code >= 300:
            return {"ok": False, "dev": False, "error": r.text[:300]}
        return {"ok": True, "dev": False, "error": None}
    except httpx.HTTPError as e:
        return {"ok": False, "dev": False, "error": str(e)[:300]}


def send_otp_email(to: str, code: str, lang: str = "uz") -> dict:
    lang = lang if lang in SUBJECTS else "uz"
    if not settings.RESEND_API_KEY:
        print(f"\n[DEV OTP] email={to}  kod={code}\n")
        return {"ok": True, "dev": True, "error": None}
    html = (
        '<div style="font-family:Arial,sans-serif;max-width:420px;margin:auto;padding:24px;'
        'border-radius:16px;border:1px solid #e5e7eb">'
        '<h2 style="color:#4f46e5;margin:0 0 8px">Learning English</h2>'
        f'<p style="color:#374151">{TEXTS[lang]}</p>'
        f'<div style="font-size:34px;letter-spacing:10px;font-weight:700;color:#111827;'
        f'background:#f3f4f6;padding:16px;text-align:center;border-radius:12px">{code}</div></div>'
    )
    return send_email(to, SUBJECTS[lang], html)
