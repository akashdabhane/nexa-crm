"""Authentication and organization access.

- `get_authenticated_user`: a valid Supabase token. Enough for account-level
  endpoints (your profile, your organizations, your invitations).
- `get_current_user`: the above plus an active membership in the organization
  named by the `X-Organization-Id` header. It scopes the request's database
  session to that organization (see `app.db.tenancy`) and sets the user's role
  for it. Every CRM endpoint uses this one.
"""

import uuid
from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import forbidden
from app.core.security import TokenError, decode_supabase_token
from app.db.session import get_db
from app.db.tenancy import set_current_org
from app.models import Membership, Profile
from app.models.enums import MembershipStatus, UserRole

bearer_scheme = HTTPBearer(auto_error=False)

ORG_HEADER = "X-Organization-Id"
# Response header that tells the frontend to send the user back to the organization picker.
ORG_ERROR_HEADER = "X-Organization-Error"


def _unauthorized(detail: str = "Not authenticated") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _organization_error(detail: str, code: int = status.HTTP_404_NOT_FOUND) -> HTTPException:
    return HTTPException(status_code=code, detail=detail, headers={ORG_ERROR_HEADER: "1"})


def _create_profile(db: Session, user_id: uuid.UUID, claims: dict) -> Profile:
    """Just-in-time provisioning: first request from a new Supabase user.

    A new account belongs to no organization: it can create one, or wait to be
    invited. It sees no CRM data until then.
    """
    email = (claims.get("email") or f"{user_id}@unknown.local").lower()
    metadata = claims.get("user_metadata") or {}
    full_name = metadata.get("full_name") or email.split("@")[0]

    profile = Profile(id=user_id, email=email, full_name=full_name)
    db.add(profile)
    try:
        db.commit()
    except IntegrityError:
        # Two simultaneous first requests: the other one created it already.
        db.rollback()
        return db.get(Profile, user_id)
    return profile


def get_authenticated_user(
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
    profile.auth_claims = claims
    return profile


def _parse_org_id(value: str | None) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(value)
    except ValueError:
        raise _organization_error("Organization not found")


def _enter_organization(db: Session, user: Profile, org_id: uuid.UUID) -> Membership:
    membership = db.scalar(
        select(Membership).where(Membership.organization_id == org_id, Membership.user_id == user.id)
    )
    # 404 either way: don't reveal whether an organization you don't belong to exists.
    if membership is None:
        raise _organization_error("Organization not found")
    if membership.status != MembershipStatus.ACTIVE:
        raise _organization_error("Your access to this organization has been disabled", status.HTTP_403_FORBIDDEN)
    set_current_org(db, org_id)
    user.org_role = membership.role
    return membership


def get_current_user(
    user: Profile = Depends(get_authenticated_user),
    org_header: str | None = Header(None, alias=ORG_HEADER),
    db: Session = Depends(get_db),
) -> Profile:
    """The signed-in member of the selected organization; the session only sees that organization's data."""
    org_id = _parse_org_id(org_header)
    if org_id is None:
        raise _organization_error("Select an organization first", status.HTTP_400_BAD_REQUEST)
    _enter_organization(db, user, org_id)
    return user


def get_user_with_optional_org(
    user: Profile = Depends(get_authenticated_user),
    org_header: str | None = Header(None, alias=ORG_HEADER),
    db: Session = Depends(get_db),
) -> Profile:
    """Like `get_current_user`, but the organization is optional (role is None without one)."""
    org_id = _parse_org_id(org_header)
    if org_id is not None:
        _enter_organization(db, user, org_id)
    return user


def require_roles(*roles: UserRole) -> Callable[..., Profile]:
    """Dependency factory: `Depends(require_roles(UserRole.ADMIN))`. Roles are per organization."""

    def checker(user: Profile = Depends(get_current_user)) -> Profile:
        if user.role not in roles:
            raise forbidden()
        return user

    return checker


require_admin = require_roles(UserRole.ADMIN)
require_manager = require_roles(UserRole.ADMIN, UserRole.MANAGER)
