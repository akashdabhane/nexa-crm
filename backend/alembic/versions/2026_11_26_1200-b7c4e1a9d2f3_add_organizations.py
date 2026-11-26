"""add organizations (multi-tenancy)

Every CRM record now belongs to an organization, and users get access through
memberships. Existing data is kept: if the database already has users or
records, they are all moved into one organization ("My Organization", which
an admin can rename) and every existing user becomes a member of it with the
role they had before.

Revision ID: b7c4e1a9d2f3
Revises: 6228d7bc5837
Create Date: 2026-11-26 12:00:00

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c4e1a9d2f3"
down_revision: Union[str, Sequence[str], None] = "6228d7bc5837"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_ORG_NAME = "My Organization"

# Every table whose rows belong to one organization.
TENANT_TABLES = (
    "companies",
    "contacts",
    "leads",
    "lead_integrations",
    "pipelines",
    "pipeline_stages",
    "deals",
    "activities",
    "notes",
    "tasks",
    "notifications",
    "audit_logs",
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["created_by_id"], ["profiles.id"], name="fk_organizations_created_by_id_profiles", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organizations"),
    )
    op.create_table(
        "memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_memberships_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["profiles.id"], name="fk_memberships_user_id_profiles", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_memberships"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_memberships_organization_user"),
    )
    op.create_index("ix_memberships_organization_id", "memberships", ["organization_id"])
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"])
    op.create_table(
        "invitations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("invited_by_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_invitations_organization_id_organizations",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["invited_by_id"], ["profiles.id"], name="fk_invitations_invited_by_id_profiles", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_invitations"),
    )
    op.create_index("ix_invitations_organization_id", "invitations", ["organization_id"])
    op.create_index("ix_invitations_email", "invitations", ["email"])

    # --- Move existing data into one organization ---------------------------
    conn = op.get_bind()
    has_data = conn.scalar(sa.text("SELECT EXISTS (SELECT 1 FROM profiles)")) or any(
        conn.scalar(sa.text(f"SELECT EXISTS (SELECT 1 FROM {table})")) for table in TENANT_TABLES
    )
    org_id = None
    if has_data:
        org_id = uuid.uuid4()
        # The longest-standing admin "creates" it (falls back to the oldest user).
        creator = conn.scalar(
            sa.text("SELECT id FROM profiles ORDER BY (role = 'admin') DESC, created_at LIMIT 1")
        )
        conn.execute(
            sa.text("INSERT INTO organizations (id, name, created_by_id) VALUES (:id, :name, :creator)"),
            {"id": org_id, "name": DEFAULT_ORG_NAME, "creator": creator},
        )
        # Everyone keeps their role, and "joined" stays the date they first signed in. A deactivated
        # user becomes a disabled member of this organization (and their account itself is
        # re-enabled, so they can still join others).
        conn.execute(
            sa.text(
                "INSERT INTO memberships (id, organization_id, user_id, role, status, created_at, updated_at) "
                "SELECT gen_random_uuid(), :org, id, role, "
                "CASE WHEN is_active THEN 'active' ELSE 'disabled' END, created_at, created_at FROM profiles"
            ),
            {"org": org_id},
        )
        conn.execute(sa.text("UPDATE profiles SET is_active = true WHERE is_active = false"))

    for table in TENANT_TABLES:
        op.add_column(table, sa.Column("organization_id", sa.Uuid(), nullable=True))
        if org_id is not None:
            conn.execute(sa.text(f"UPDATE {table} SET organization_id = :org"), {"org": org_id})
        op.alter_column(table, "organization_id", nullable=False)
        op.create_index(f"ix_{table}_organization_id", table, ["organization_id"])
        op.create_foreign_key(
            f"fk_{table}_organization_id_organizations",
            table,
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # Imported-lead de-duplication is now per organization.
    op.drop_constraint("uq_leads_social_platform_external_id", "leads", type_="unique")
    op.create_unique_constraint(
        "uq_leads_organization_platform_external_id", "leads", ["organization_id", "social_platform", "external_id"]
    )

    # Roles now live on memberships.
    op.drop_column("profiles", "role")


def downgrade() -> None:
    """Back to a single shared workspace. Fails if two organizations imported the same social lead."""
    op.add_column(
        "profiles", sa.Column("role", sa.String(length=20), nullable=False, server_default="sales_rep")
    )
    # A user's strongest role in any organization.
    op.execute(
        "UPDATE profiles p SET role = m.role FROM ("
        "  SELECT DISTINCT ON (user_id) user_id, role FROM memberships"
        "  ORDER BY user_id, CASE role WHEN 'admin' THEN 0 WHEN 'manager' THEN 1 ELSE 2 END"
        ") m WHERE m.user_id = p.id"
    )
    op.alter_column("profiles", "role", server_default=None)

    op.drop_constraint("uq_leads_organization_platform_external_id", "leads", type_="unique")
    op.create_unique_constraint("uq_leads_social_platform_external_id", "leads", ["social_platform", "external_id"])

    for table in reversed(TENANT_TABLES):
        op.drop_constraint(f"fk_{table}_organization_id_organizations", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_organization_id", table_name=table)
        op.drop_column(table, "organization_id")

    op.drop_index("ix_invitations_email", table_name="invitations")
    op.drop_index("ix_invitations_organization_id", table_name="invitations")
    op.drop_table("invitations")
    op.drop_index("ix_memberships_user_id", table_name="memberships")
    op.drop_index("ix_memberships_organization_id", table_name="memberships")
    op.drop_table("memberships")
    op.drop_table("organizations")
