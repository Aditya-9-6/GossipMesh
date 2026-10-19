import os

<<<<<<< HEAD
def get_env_flag(flag_name):
    """Get the value of an environment flag, defaulting to False if not set."""
    return os.getenv(flag_name, "false").lower() == "true"
=======
from gossipmesh.db.session import SessionLocal
from gossipmesh.core.config import settings
from gossipmesh.models.user import User
from gossipmesh.core.exceptions import AuthenticationError, AuthorizationError
from gossipmesh.db.redis import redis_client

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login/access-token"
)

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

from datetime import timedelta
from gossipmesh.models.session import UserSession

def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
            leeway=timedelta(seconds=10)
        )
        token_type = payload.get("type")
        if token_type != "access":
            raise AuthenticationError(message="Invalid token type")

        user_id = payload.get("sub")
        session_id = payload.get("sid")
        jti = payload.get("jti")
        iat = payload.get("iat")

        if user_id is None:
            raise AuthenticationError(message="Could not validate credentials")

        if session_id:
            session = db.query(UserSession).filter(UserSession.id == session_id).first()
            if not session or not session.is_active:
                raise AuthenticationError(message="Session is inactive")

        # Check token blocklist
        if jti and redis_client.exists(f"revoked_token:{jti}"):
            raise AuthenticationError(message="Token has been revoked")

        # Check session invalidation (password change)
        if iat:
            invalidated_before = redis_client.get(f"sessions_invalidated_before:{user_id}")
            if invalidated_before and float(iat) < float(invalidated_before):
                raise AuthenticationError(message="Session has been invalidated")

    except (jwt.InvalidTokenError, ValidationError):
        raise AuthenticationError(message="Could not validate credentials")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AuthenticationError(message="User not found")
    if not user.is_active:
        raise AuthorizationError(message="Inactive user")
    return user
>>>>>>> origin/main


# Environment-controlled flags
GOSSIPMESH_AUTOMATION_ENABLED = get_env_flag("GOSSIPMESH_AUTOMATION_ENABLED")
GOSSIPMESH_ALLOW_PR_CREATION = get_env_flag("GOSSIPMESH_ALLOW_PR_CREATION")
GOSSIPMESH_ALLOW_PUSH = get_env_flag("GOSSIPMESH_ALLOW_PUSH")
GOSSIPMESH_ALLOW_FORCE_PUSH = get_env_flag("GOSSIPMESH_ALLOW_FORCE_PUSH")
GOSSIPMESH_ALLOW_AUTO_MERGE = get_env_flag("GOSSIPMESH_ALLOW_AUTO_MERGE")
GOSSIPMESH_MAX_FILES_PER_CHANGE = int(os.getenv("GOSSIPMESH_MAX_FILES_PER_CHANGE", "10"))
GOSSIPMESH_MAX_DAILY_RUNS = int(os.getenv("GOSSIPMESH_MAX_DAILY_RUNS", "100"))
GOSSIPMESH_MAX_DAILY_PR_CREATION = int(os.getenv("GOSSIPMESH_MAX_DAILY_PR_CREATION", "10"))

# Default PR creation, push, force-push, and auto-merge to disabled
if not GOSSIPMESH_ALLOW_PR_CREATION:
    print("PR creation is disabled.")
if not GOSSIPMESH_ALLOW_PUSH:
    print("Push is disabled.")
if not GOSSIPMESH_ALLOW_FORCE_PUSH:
    print("Force push is disabled.")
if not GOSSIPMESH_ALLOW_AUTO_MERGE:
    print("Auto merge is disabled.")

# Add checks in autonomous scripts
# ... (add your autonomous script checks here)

# Add tests for the new behavior
# ... (add your tests here)
