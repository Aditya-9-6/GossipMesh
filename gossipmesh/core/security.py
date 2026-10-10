from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from cryptography.fernet import Fernet
import jwt
from typing import Any

from gossipmesh.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
fernet = Fernet(settings.ENCRYPTION_KEY.encode() if isinstance(settings.ENCRYPTION_KEY, str) else settings.ENCRYPTION_KEY)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return whether the plaintext password matches the stored bcrypt hash.

    Hash parsing and verification errors propagate rather than returning False.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Return a salted bcrypt hash; hashing errors propagate."""
    return pwd_context.hash(password)

def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    """Return a signed JWT with the subject converted to a string.

    Expiration is measured from the current UTC time. A missing or zero
    expires_delta uses ACCESS_TOKEN_EXPIRE_MINUTES; a negative duration
    produces an already expired token. JWT encoding errors propagate.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def encrypt_string(plain_text: str) -> str:
    """Return a Fernet token for UTF-8 text using the configured encryption key."""
    return fernet.encrypt(plain_text.encode()).decode()

def decrypt_string(encrypted_text: str) -> str:
    """Decrypt a Fernet token with the configured key and return UTF-8 text.

    InvalidToken propagates for invalid tokens or a mismatched key, and
    UnicodeDecodeError propagates if the decrypted bytes are not UTF-8.
    Token age is not checked.
    """
    return fernet.decrypt(encrypted_text.encode()).decode()
