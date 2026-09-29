"""Remove indexes duplicated by unique constraints.

Revision ID: 0004_remove_unique_indexes
Revises: 0003_align_schema
Create Date: 2026-09-28
"""

from alembic import op


revision = "0004_remove_unique_indexes"
down_revision = "0003_align_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The unique constraints created in 0001 already create the required
    # PostgreSQL indexes.  0003's explicit unique indexes duplicate them.
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_tournaments_slug", table_name="tournaments")


def downgrade() -> None:
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_tournaments_slug", "tournaments", ["slug"], unique=True)
