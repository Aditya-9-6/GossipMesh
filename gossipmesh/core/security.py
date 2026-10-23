from datetime import datetime, timedelta, timezone
import uuid
from typing import Any
import bcrypt
from cryptography.fernet import Fernet
import jwt

from gossipmesh.core.config import settings

fernet = Fernet(
    settings.ENCRYPTION_KEY.encode() if isinstance(settings.ENCRYPTION_KEY, str) else settings.ENCRYPTION_KEY
)


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password[:72].encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    # Truncate at 72 bytes per bcrypt standard
    return bcrypt.hashpw(password[:72].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(
    subject: str | Any, session_id: int | None = None, expires_delta: timedelta | None = None
) -> str:
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "exp": expire,
        "iat": now,
        "nbf": now,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "sub": str(subject),
        "jti": str(uuid.uuid4()),
        "type": "access",
    }
    if session_id:
        to_encode["sid"] = str(session_id)

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    subject: str | Any, session_id: int | None = None, jti: str | None = None, expires_delta: timedelta | None = None
) -> str:
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "exp": expire,
        "iat": now,
        "nbf": now,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "sub": str(subject),
        "jti": jti or str(uuid.uuid4()),
        "type": "refresh",
    }
    if session_id:
        to_encode["sid"] = str(session_id)

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt if isinstance(encoded_jwt, str) else encoded_jwt.decode("utf-8")


def encrypt_string(plain_text: str) -> str:
    return fernet.encrypt(plain_text.encode()).decode()


def decrypt_string(encrypted_text: str) -> str:
    return fernet.decrypt(encrypted_text.encode()).decode()
