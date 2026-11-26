"""Record-level authorization rules, inside the current organization.

- Members can read every record of their organization (other organizations'
  records are invisible: see `app.db.tenancy`).
- Admins/Managers can edit, reassign and delete anything.
- Sales reps can edit only records they own, can't reassign, and always own
  what they create.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import bad_request, forbidden
from app.db.tenancy import current_org
from app.models import Membership, Profile
from app.models.enums import MembershipStatus


def ensure_can_edit(user: Profile, record, owner_field: str = "owner_id") -> None:
    if user.is_manager_or_admin:
        return
    if getattr(record, owner_field) != user.id:
        raise forbidden("You can only modify records assigned to you")


def owner_for_create(db: Session, user: Profile, requested: uuid.UUID | None) -> uuid.UUID:
    """Owner of a new record: reps always own their records; managers may assign."""
    if requested is None or requested == user.id:
        return user.id
    if not user.is_manager_or_admin:
        raise forbidden("Only managers and admins can assign records to other users")
    ensure_user_exists(db, requested)
    return requested


def check_owner_change(db: Session, user: Profile, record, new_owner: uuid.UUID | None) -> None:
    """Validate an owner change on update (only called when owner_id was sent)."""
    if new_owner == record.owner_id:
        return
    if not user.is_manager_or_admin:
        raise forbidden("Only managers and admins can reassign records")
    if new_owner is not None:
        ensure_user_exists(db, new_owner)


def is_active_member(db: Session, user_id: uuid.UUID, org_id: uuid.UUID | None = None) -> bool:
    """Whether the user can currently work in the organization (default: the current one)."""
    org_id = org_id or current_org(db)
    if org_id is None:
        return False
    found = db.scalar(
        select(Membership.id)
        .join(Profile, Profile.id == Membership.user_id)
        .where(
            Membership.organization_id == org_id,
            Membership.user_id == user_id,
            Membership.status == MembershipStatus.ACTIVE,
            Profile.is_active.is_(True),
        )
    )
    return found is not None


def ensure_user_exists(db: Session, user_id: uuid.UUID) -> None:
    """Records can only be assigned to active members of the current organization."""
    if not is_active_member(db, user_id):
        raise bad_request("Assigned user does not exist or is inactive")
