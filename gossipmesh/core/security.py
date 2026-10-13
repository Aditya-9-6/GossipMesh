from datetime import datetime, timedelta, timezone
import uuid
import string
import re
from passlib.context import CryptContext
from cryptography.fernet import Fernet
import jwt
from typing import Any

from gossipmesh.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
fernet = Fernet(settings.ENCRYPTION_KEY.encode() if isinstance(settings.ENCRYPTION_KEY, str) else settings.ENCRYPTION_KEY)

def validate_password_strength(password: str) -> None:
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not any(char.isupper() for char in password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not any(char.islower() for char in password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not any(char.isdigit() for char in password):
        raise ValueError("Password must contain at least one digit")
    if not any(char in string.punctuation for char in password):
        raise ValueError("Password must contain at least one special character")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def dummy_verify() -> None:
    """Run a dummy verification to mitigate timing attacks."""
    pwd_context.dummy_verify()

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    iat = datetime.now(timezone.utc)
    jti = str(uuid.uuid4())

    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": iat,
        "jti": jti
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def encrypt_string(plain_text: str) -> str:
    return fernet.encrypt(plain_text.encode()).decode()

def decrypt_string(encrypted_text: str) -> str:
    return fernet.decrypt(encrypted_text.encode()).decode()
