"""Organizations, and how people get into them.

Anyone signed in can create an organization (they become its admin) and see
the organizations they belong to. Access to an existing organization is only
granted by its admins, through an invitation to the person's email address;
the person accepts it after signing in with that (confirmed) email.
"""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased

from app.core.exceptions import bad_request, not_found
from app.db.session import get_db
from app.db.tenancy import current_org, set_current_org
from app.dependencies.auth import get_authenticated_user, get_current_user, require_admin
from app.models import Invitation, Membership, Organization, Profile
from app.models.enums import MembershipStatus
from app.schemas.organization import (
    InvitationCreate,
    InvitationRead,
    MyInvitation,
    MyOrganization,
    OrganizationCreate,
    OrganizationRead,
    OrganizationUpdate,
)
from app.services import audit
from app.services.pipelines import create_default_pipeline

router = APIRouter(tags=["organizations"])

INVITATION_TTL = timedelta(days=14)


def _my_organizations(db: Session, user: Profile) -> list[dict]:
    members = aliased(Membership)
    member_count = (
        select(func.count())
        .select_from(members)
        .where(members.organization_id == Organization.id, members.status == MembershipStatus.ACTIVE)
        .correlate(Organization)
        .scalar_subquery()
    )
    rows = db.execute(
        select(Organization, Membership.role, Membership.status, member_count)
        .join(Membership, Membership.organization_id == Organization.id)
        .where(Membership.user_id == user.id)
        .order_by(Organization.name)
    ).all()
    return [
        {"id": org.id, "name": org.name, "created_at": org.created_at, "role": role, "status": st, "member_count": n}
        for org, role, st, n in rows
    ]


@router.get("/organizations", response_model=list[MyOrganization])
def list_my_organizations(user: Profile = Depends(get_authenticated_user), db: Session = Depends(get_db)):
    """Only the organizations you are a member of; others are never listed."""
    return _my_organizations(db, user)


@router.post("/organizations", response_model=MyOrganization, status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreate, user: Profile = Depends(get_authenticated_user), db: Session = Depends(get_db)
):
    """Start a new, empty organization. You become its admin."""
    org = Organization(name=payload.name, created_by_id=user.id)
    db.add(org)
    db.flush()
    db.add(Membership(organization_id=org.id, user_id=user.id, role="admin", status=MembershipStatus.ACTIVE))
    set_current_org(db, org.id)
    create_default_pipeline(db)
    audit.record(db, user, "organization.created", "organization", org.id, name=org.name)
    db.commit()
    return {
        "id": org.id,
        "name": org.name,
        "created_at": org.created_at,
        "role": "admin",
        "status": MembershipStatus.ACTIVE,
        "member_count": 1,
    }


@router.get("/organizations/current", response_model=OrganizationRead)
def get_current_organization(_: Profile = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.get(Organization, current_org(db))


@router.patch("/organizations/current", response_model=OrganizationRead)
def rename_organization(
    payload: OrganizationUpdate, admin: Profile = Depends(require_admin), db: Session = Depends(get_db)
):
    org = db.get(Organization, current_org(db))
    changes = audit.apply_changes(org, {"name": payload.name})
    if changes:
        audit.record(db, admin, "organization.renamed", "organization", org.id, changes=changes)
    db.commit()
    return org


# --- Invitations (admins of the current organization) ------------------------


def _open(stmt):
    return stmt.where(Invitation.accepted_at.is_(None), Invitation.expires_at > func.now())


@router.get("/invitations", response_model=list[InvitationRead])
def list_invitations(_: Profile = Depends(require_admin), db: Session = Depends(get_db)):
    """Pending invitations to the current organization."""
    return db.scalars(
        _open(select(Invitation).where(Invitation.organization_id == current_org(db))).order_by(
            Invitation.created_at.desc()
        )
    ).all()


@router.post("/invitations", response_model=InvitationRead, status_code=status.HTTP_201_CREATED)
def invite_member(payload: InvitationCreate, admin: Profile = Depends(require_admin), db: Session = Depends(get_db)):
    """Invite an email address. Inviting the same address again refreshes the open invitation."""
    org_id = current_org(db)
    email = payload.email.lower()
    already_member = db.scalar(
        select(Membership.id)
        .join(Profile, Profile.id == Membership.user_id)
        .where(
            Membership.organization_id == org_id,
            func.lower(Profile.email) == email,
            Membership.status == MembershipStatus.ACTIVE,
        )
    )
    if already_member:
        raise bad_request("This person is already a member of the organization")

    expires_at = datetime.now(UTC) + INVITATION_TTL
    invitation = db.scalar(
        select(Invitation).where(
            Invitation.organization_id == org_id, Invitation.email == email, Invitation.accepted_at.is_(None)
        )
    )
    if invitation is None:
        invitation = Invitation(organization_id=org_id, email=email)
        db.add(invitation)
    invitation.role = payload.role
    invitation.invited_by_id = admin.id
    invitation.expires_at = expires_at
    db.flush()
    audit.record(db, admin, "member.invited", "invitation", invitation.id, email=email, role=payload.role)
    db.commit()
    db.refresh(invitation)
    return invitation


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invitation(invitation_id: uuid.UUID, admin: Profile = Depends(require_admin), db: Session = Depends(get_db)):
    invitation = db.get(Invitation, invitation_id)
    if invitation is None or invitation.organization_id != current_org(db) or invitation.accepted_at is not None:
        raise not_found("Invitation")
    audit.record(db, admin, "member.invitation_revoked", "invitation", invitation.id, email=invitation.email)
    db.delete(invitation)
    db.commit()


# --- Invitations addressed to you --------------------------------------------


def _my_invitation(db: Session, user: Profile, invitation_id: uuid.UUID) -> Invitation:
    email = user.verified_email
    invitation = db.get(Invitation, invitation_id)
    if (
        email is None
        or invitation is None
        or invitation.email != email
        or invitation.accepted_at is not None
        or invitation.expires_at <= datetime.now(UTC)
    ):
        raise not_found("Invitation")
    return invitation


@router.get("/me/invitations", response_model=list[MyInvitation])
def list_my_invitations(user: Profile = Depends(get_authenticated_user), db: Session = Depends(get_db)):
    """Open invitations sent to the email you signed in with."""
    email = user.verified_email
    if email is None:
        return []
    return db.scalars(_open(select(Invitation).where(Invitation.email == email)).order_by(Invitation.created_at)).all()


@router.post("/me/invitations/{invitation_id}/accept", response_model=MyOrganization)
def accept_invitation(
    invitation_id: uuid.UUID, user: Profile = Depends(get_authenticated_user), db: Session = Depends(get_db)
):
    invitation = _my_invitation(db, user, invitation_id)
    org_id = invitation.organization_id
    membership = db.scalar(select(Membership).where(Membership.organization_id == org_id, Membership.user_id == user.id))
    if membership is None:
        membership = Membership(organization_id=org_id, user_id=user.id)
        db.add(membership)
    # An admin re-inviting a disabled member restores their access with the invited role.
    membership.role = invitation.role
    membership.status = MembershipStatus.ACTIVE
    invitation.accepted_at = datetime.now(UTC)
    set_current_org(db, org_id)
    audit.record(db, user, "member.joined", "user", user.id, name=user.full_name, role=invitation.role)
    db.commit()
    return next(org for org in _my_organizations(db, user) if org["id"] == org_id)


@router.post("/me/invitations/{invitation_id}/decline", status_code=status.HTTP_204_NO_CONTENT)
def decline_invitation(
    invitation_id: uuid.UUID, user: Profile = Depends(get_authenticated_user), db: Session = Depends(get_db)
):
    invitation = _my_invitation(db, user, invitation_id)
    db.delete(invitation)
    db.commit()
