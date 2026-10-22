"""
Multi-Factor Authentication (MFA / TOTP) Service.
Implements RFC 6238 Time-Based One-Time Passwords (TOTP), recovery codes,
and enterprise step-up authentication gates for destructive operations.
"""

import base64
import hashlib
import hmac
import secrets
import struct
import time
from typing import List, Tuple
from sqlalchemy.orm import Session

from gossipmesh.core.exceptions import GossipMeshException


class MFAAuthenticationError(GossipMeshException):
    """Raised when MFA verification fails or step-up authentication is rejected."""

    pass


def generate_totp_secret(length: int = 20) -> str:
    """Generate a cryptographically secure Base32-encoded secret for TOTP."""
    raw_bytes = secrets.token_bytes(length)
    return base64.b32encode(raw_bytes).decode("utf-8").replace("=", "")


def get_totp_token(secret: str, time_step: int = 30, t: float | None = None) -> str:
    """
    Compute 6-digit TOTP token using RFC 6238 (HMAC-SHA1).
    """
    if t is None:
        t = time.time()

    counter = int(t // time_step)
    counter_bytes = struct.pack(">Q", counter)

    # Pad secret if padding was stripped
    padded_secret = secret
    missing_padding = len(padded_secret) % 8
    if missing_padding != 0:
        padded_secret += "=" * (8 - missing_padding)

    try:
        key = base64.b32decode(padded_secret.upper())
    except Exception as e:
        raise MFAAuthenticationError(f"Invalid Base32 TOTP secret: {e}")

    hmac_digest = hmac.new(key, counter_bytes, hashlib.sha1).digest()
    offset = hmac_digest[-1] & 0x0F
    code_int = struct.unpack(">I", hmac_digest[offset : offset + 4])[0] & 0x7FFFFFFF
    code = code_int % 1000000
    return f"{code:06d}"


def verify_totp_code(secret: str, code: str, time_step: int = 30, window: int = 1) -> bool:
    """
    Verify TOTP code against secret, checking current interval and +/- window steps for clock drift.
    """
    if not code or not code.strip().isdigit() or len(code.strip()) != 6:
        return False

    code = code.strip()
    current_time = time.time()

    for step_offset in range(-window, window + 1):
        check_time = current_time + (step_offset * time_step)
        expected = get_totp_token(secret, time_step=time_step, t=check_time)
        if hmac.compare_digest(expected, code):
            return True

    return False


def generate_recovery_codes(count: int = 8) -> List[str]:
    """Generate cryptographically secure one-time backup recovery codes."""
    codes = []
    for _ in range(count):
        chunk1 = secrets.token_hex(2).upper()
        chunk2 = secrets.token_hex(2).upper()
        codes.append(f"{chunk1}-{chunk2}")
    return codes


class MFAService:
    """Enterprise MFA Management & Step-Up Auth Enforcement."""

    @staticmethod
    def setup_mfa_for_user(user_id: int, db: Session) -> Tuple[str, List[str]]:
        """
        Initiate MFA setup: generates a new secret and recovery codes.
        Does not activate MFA until verified with a valid token.
        """
        from gossipmesh.models.user import User

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise MFAAuthenticationError(f"User #{user_id} not found")

        secret = generate_totp_secret()
        recovery_codes = generate_recovery_codes()

        user.mfa_secret = secret
        user.mfa_enabled = False
        db.commit()
        db.refresh(user)

        return secret, recovery_codes

    @staticmethod
    def verify_and_activate(user_id: int, code: str, db: Session) -> bool:
        """
        Verify code against newly setup secret and mark MFA as enabled.
        """
        from gossipmesh.models.user import User

        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.mfa_secret:
            raise MFAAuthenticationError("MFA setup has not been initiated for this user")

        if not verify_totp_code(user.mfa_secret, code):
            raise MFAAuthenticationError("Invalid MFA TOTP verification code")

        user.mfa_enabled = True
        db.commit()
        db.refresh(user)
        return True

    @staticmethod
    def require_step_up_auth(user, mfa_code: str | None, operation_name: str = "destructive_action") -> bool:
        """
        Enforce step-up authentication for sensitive/destructive operations
        (e.g., organization deletion, audit log export, break-glass invocation).
        """
        if not getattr(user, "mfa_enabled", False):
            # If user has not enabled MFA, require MFA setup before allowing destructive enterprise action
            raise MFAAuthenticationError(
                f"Operation '{operation_name}' requires Multi-Factor Authentication (MFA) to be enabled on your account."
            )

        if not mfa_code:
            raise MFAAuthenticationError(
                f"Step-up authentication required for '{operation_name}'. Please provide a valid 6-digit TOTP code."
            )

        secret = getattr(user, "mfa_secret", None)
        if not secret or not verify_totp_code(secret, mfa_code):
            raise MFAAuthenticationError(f"Invalid TOTP step-up authentication code for operation '{operation_name}'.")

        return True
