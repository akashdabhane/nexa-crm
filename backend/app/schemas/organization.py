import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.models.enums import MembershipStatus, UserRole
from app.schemas.common import InputSchema, ORMSchema
from app.schemas.profile import ProfileSummary


class OrganizationCreate(InputSchema):
    name: str = Field(min_length=1, max_length=100)


class OrganizationUpdate(InputSchema):
    name: str = Field(min_length=1, max_length=100)


class OrganizationRead(ORMSchema):
    id: uuid.UUID
    name: str
    created_at: datetime


class MyOrganization(OrganizationRead):
    """An organization you belong to, with your role in it."""

    role: UserRole
    status: MembershipStatus
    member_count: int


class InvitationCreate(InputSchema):
    email: EmailStr
    role: UserRole = UserRole.SALES_REP


class InvitationRead(ORMSchema):
    id: uuid.UUID
    email: str
    role: UserRole
    invited_by: ProfileSummary | None
    created_at: datetime
    expires_at: datetime


class MyInvitation(ORMSchema):
    """An invitation addressed to you."""

    id: uuid.UUID
    organization: OrganizationRead
    role: UserRole
    invited_by: ProfileSummary | None
    expires_at: datetime
