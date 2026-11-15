import httpx

from config import settings

ESKIZ_URL = "https://notify.eskiz.uz/api/message/sms/send"


def send_sms(phone: str, text: str) -> dict:
    """-> {"ok": bool, "dev": bool, "error": str|None}.
    SMS_PROVIDER=eskiz  -> Eskiz.uz (SMS_API_KEY = tayyor token)
    SMS_PROVIDER=generic -> SMS_API_URL ga Bearer SMS_API_KEY bilan JSON POST {"to","text"}
    Hech narsa sozlanmagan bo'lsa DEV rejimi: matn konsolga chiqadi."""
    provider = settings.SMS_PROVIDER
    if not provider or not settings.SMS_API_KEY:
        print(f"\n[DEV SMS] to={phone}\n{text}\n")
        return {"ok": True, "dev": True, "error": None}
    try:
        if provider == "eskiz":
            r = httpx.post(
                settings.SMS_API_URL or ESKIZ_URL,
                headers={"Authorization": f"Bearer {settings.SMS_API_KEY}"},
                data={"mobile_phone": phone.lstrip("+"), "message": text, "from": "4546"},
                timeout=15,
            )
        else:
            if not settings.SMS_API_URL:
                return {"ok": False, "dev": False, "error": "SMS_API_URL is empty"}
            r = httpx.post(
                settings.SMS_API_URL,
                headers={"Authorization": f"Bearer {settings.SMS_API_KEY}"},
                json={"to": phone, "text": text},
                timeout=15,
            )
        if r.status_code >= 300:
            return {"ok": False, "dev": False, "error": r.text[:300]}
        return {"ok": True, "dev": False, "error": None}
    except httpx.HTTPError as e:
        return {"ok": False, "dev": False, "error": str(e)[:300]}


def _origin_host() -> str:
    from urllib.parse import urlparse
    return urlparse(settings.FRONTEND_URL).hostname or "localhost"


def send_otp_sms(phone: str, code: str, lang: str = "uz") -> dict:
    # Oxirgi qator "@domen #kod" formati: Android Chrome (WebOTP) kodni sahifaga o'zi kiritadi,
    # iOS esa autocomplete="one-time-code" orqali klaviaturada taklif qiladi.
    tail = f"\n\n@{_origin_host()} #{code}"
    texts = {
        "uz": f"Learning English tasdiqlash kodi: {code}. 10 daqiqa amal qiladi." + tail,
        "en": f"Learning English verification code: {code}. Valid for 10 minutes." + tail,
        "ru": f"Код подтверждения Learning English: {code}. Действует 10 минут." + tail,
    }
    if not settings.SMS_PROVIDER or not settings.SMS_API_KEY:
        print(f"\n[DEV OTP] telefon={phone}  kod={code}\n")
        return {"ok": True, "dev": True, "error": None}
    return send_sms(phone, texts.get(lang, texts["uz"]))
