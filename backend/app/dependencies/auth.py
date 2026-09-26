import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import forbidden
from app.core.security import TokenError, decode_supabase_token
from app.db.session import get_db
from app.models import Profile
from app.models.enums import UserRole

bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _create_profile(db: Session, user_id: uuid.UUID, claims: dict) -> Profile:
    """Just-in-time provisioning: first request from a new Supabase user.

    If no Admin exists yet (fresh install, or only seeded demo users), the new
    user becomes Admin so the app can always be administered.
    """
    email = claims.get("email") or f"{user_id}@unknown.local"
    metadata = claims.get("user_metadata") or {}
    full_name = metadata.get("full_name") or email.split("@")[0]
    has_admin = db.scalar(select(func.count()).select_from(Profile).where(Profile.role == UserRole.ADMIN)) > 0

    profile = Profile(
        id=user_id,
        email=email,
        full_name=full_name,
        role=UserRole.SALES_REP if has_admin else UserRole.ADMIN,
    )
    db.add(profile)
    try:
        db.commit()
    except IntegrityError:
        # Two simultaneous first requests: the other one created it already.
        db.rollback()
        return db.get(Profile, user_id)
    return profile


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Profile:
    if credentials is None:
        raise _unauthorized()
    try:
        claims = decode_supabase_token(credentials.credentials)
        user_id = uuid.UUID(claims["sub"])
    except (TokenError, ValueError):
        raise _unauthorized("Invalid or expired token")

    profile = db.get(Profile, user_id) or _create_profile(db, user_id, claims)
    if not profile.is_active:
        raise forbidden("Your account has been deactivated")
    return profile


def require_roles(*roles: UserRole) -> Callable[..., Profile]:
    """Dependency factory: `Depends(require_roles(UserRole.ADMIN))`."""

    def checker(user: Profile = Depends(get_current_user)) -> Profile:
        if user.role not in roles:
            raise forbidden()
        return user

    return checker


require_admin = require_roles(UserRole.ADMIN)
require_manager = require_roles(UserRole.ADMIN, UserRole.MANAGER)
