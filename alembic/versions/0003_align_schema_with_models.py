"""Align indexes and user email length with current ORM models.

Revision ID: 0003_align_schema
Revises: 0002_user_role_is_admin
Create Date: 2026-09-28
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_align_schema"
down_revision = "0002_user_role_is_admin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLAlchemy's ``unique=True, index=True`` creates a unique index. The
    # original migration created regular indexes plus unique constraints.
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_tournaments_slug", table_name="tournaments")
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_tournaments_slug", "tournaments", ["slug"], unique=True)

    # batch_alter_table works on SQLite (used in tests) and PostgreSQL.
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "email",
            existing_type=sa.String(length=100),
            type_=sa.String(length=255),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "email",
            existing_type=sa.String(length=255),
            type_=sa.String(length=100),
            existing_nullable=False,
        )

    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_tournaments_slug", table_name="tournaments")
    op.create_index("ix_users_username", "users", ["username"])
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_tournaments_slug", "tournaments", ["slug"])
