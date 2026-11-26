import uuid

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.enums import UserRole


class Profile(TimestampMixin, Base):
    """A person's login. `id` is the Supabase auth user id (JWT `sub`).

    Profiles are global; roles are not. A user's role comes from their
    `Membership` in the organization of the current request, which
    `get_current_user` copies onto `org_role` (a plain attribute, never stored).
    """

    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    # Global kill switch for the whole account (all organizations). Per-org access is Membership.status.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Set per request by the auth dependencies; not columns.
    org_role = None
    auth_claims = None  # the verified Supabase token's claims

    @property
    def verified_email(self) -> str | None:
        """The email this sign-in proves, lowercased; None if Supabase says it isn't confirmed."""
        claims = self.auth_claims or {}
        if (claims.get("user_metadata") or {}).get("email_verified") is False:
            return None
        email = claims.get("email") or self.email
        return email.lower() if email else None

    @property
    def role(self) -> str | None:
        return self.org_role

    @property
    def is_manager_or_admin(self) -> bool:
        return self.org_role in (UserRole.ADMIN, UserRole.MANAGER)
