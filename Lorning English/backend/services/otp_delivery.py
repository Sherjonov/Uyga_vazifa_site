"""Telefon raqamga tasdiqlash kodini SMS orqali yetkazish."""
from services.sms_service import send_otp_sms

def deliver_phone_otp(phone: str, code: str, lang: str = "uz") -> dict:
    result = send_otp_sms(phone, code, lang)
    return {**result, "via": "dev" if result.get("dev") else "sms"}
