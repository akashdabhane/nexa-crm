"""Your profile, and the members of the current organization.

Member management (role, enable/disable, remove) changes the person's
membership in this organization only, never their account.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import bad_request, not_found
from app.db.session import get_db
from app.db.tenancy import current_org
from app.dependencies.auth import get_current_user, get_user_with_optional_org, require_admin
from app.models import Membership, Profile
from app.models.enums import MembershipStatus, UserRole
from app.schemas.profile import ProfileRead, ProfileUpdateAdmin, ProfileUpdateMe
from app.services import audit

router = APIRouter(tags=["users"])


def member_read(membership: Membership) -> ProfileRead:
    user = membership.user
    return ProfileRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=membership.role,
        is_active=membership.is_active and user.is_active,
        created_at=membership.created_at,
    )


def _membership(db: Session, user_id: uuid.UUID) -> Membership:
    membership = db.scalar(
        select(Membership).where(Membership.organization_id == current_org(db), Membership.user_id == user_id)
    )
    if membership is None:
        raise not_found("User")
    return membership


def _other_active_admins(db: Session, membership: Membership) -> int:
    return db.scalar(
        select(func.count())
        .select_from(Membership)
        .where(
            Membership.organization_id == membership.organization_id,
            Membership.role == UserRole.ADMIN,
            Membership.status == MembershipStatus.ACTIVE,
            Membership.id != membership.id,
        )
    )


@router.get("/me", response_model=ProfileRead)
def read_me(user: Profile = Depends(get_user_with_optional_org)):
    """Your profile. `role` is your role in the organization sent in X-Organization-Id (null without one)."""
    return user


@router.patch("/me", response_model=ProfileRead)
def update_me(
    payload: ProfileUpdateMe,
    user: Profile = Depends(get_user_with_optional_org),
    db: Session = Depends(get_db),
):
    user.full_name = payload.full_name
    db.commit()
    return user


@router.get("/users", response_model=list[ProfileRead])
def list_users(
    _: Profile = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Members of the current organization: for 'assign to' dropdowns and the admin users page."""
    memberships = db.scalars(
        select(Membership)
        .join(Profile, Profile.id == Membership.user_id)
        .where(Membership.organization_id == current_org(db))
        .order_by(Profile.full_name)
    ).all()
    return [member_read(m) for m in memberships]


@router.patch("/users/{user_id}", response_model=ProfileRead)
def update_user(
    user_id: uuid.UUID,
    payload: ProfileUpdateAdmin,
    admin: Profile = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Change a member's role in this organization, or disable / re-enable their access to it."""
    membership = _membership(db, user_id)
    if user_id == admin.id and (payload.role not in (None, admin.role) or payload.is_active is False):
        raise bad_request("You cannot change your own role or deactivate yourself")

    changes = {}
    if payload.role is not None:
        changes["role"] = payload.role
    if payload.is_active is not None:
        changes["status"] = MembershipStatus.ACTIVE if payload.is_active else MembershipStatus.DISABLED
    loses_admin = membership.role == UserRole.ADMIN and (
        changes.get("role", UserRole.ADMIN) != UserRole.ADMIN or changes.get("status") == MembershipStatus.DISABLED
    )
    if loses_admin and _other_active_admins(db, membership) == 0:
        raise bad_request("An organization needs at least one active admin")

    diff = audit.apply_changes(membership, changes)
    if diff:
        audit.record(db, admin, "member.updated", "user", user_id, name=membership.user.full_name, changes=diff)
    db.commit()
    return member_read(membership)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user(user_id: uuid.UUID, admin: Profile = Depends(require_admin), db: Session = Depends(get_db)):
    """Remove someone from this organization. Their records stay, still attributed to them."""
    if user_id == admin.id:
        raise bad_request("You cannot remove yourself")
    membership = _membership(db, user_id)
    if membership.role == UserRole.ADMIN and _other_active_admins(db, membership) == 0:
        raise bad_request("An organization needs at least one active admin")
    audit.record(db, admin, "member.removed", "user", user_id, name=membership.user.full_name)
    db.delete(membership)
    db.commit()
