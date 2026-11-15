import hashlib
import hmac
from datetime import timedelta
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

from config import settings
from utils import utcnow

ALGORITHM = "HS256"
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _pwd.verify(password, hashed)
    except Exception:
        return False


def create_token(sub: str, typ: str = "access", minutes: Optional[int] = None, **extra) -> str:
    exp = utcnow() + timedelta(minutes=minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(sub), "typ": typ, "exp": exp, **extra}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def hash_code(code: str) -> str:
    return hashlib.sha256(f"{settings.SECRET_KEY}:{code}".encode()).hexdigest()


def codes_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)


def role_allowed(user, roles) -> bool:
    return user.role in roles
