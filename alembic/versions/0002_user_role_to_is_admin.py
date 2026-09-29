"""Replace user_role enum with is_admin boolean.

Revision ID: 0002_user_role_is_admin
Revises: 0001_teams_matches
Create Date: 2026-09-28
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_user_role_is_admin"
down_revision = "0001_teams_matches"
branch_labels = None
depends_on = None


user_role = sa.Enum("organizer", "manager", name="user_role")


def upgrade() -> None:
    # Add the is_admin column with a default of false
    op.add_column(
        "users",
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    # Migrate existing data: organizers become admins
    op.execute("UPDATE users SET is_admin = true WHERE user_role = 'organizer'")
    # Drop the old enum column and its type
    op.drop_column("users", "user_role")
    user_role.drop(op.get_bind(), checkfirst=True)


def downgrade() -> None:
    user_role.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "users",
        sa.Column("user_role", user_role, nullable=False, server_default="manager"),
    )
    op.execute("UPDATE users SET user_role = 'organizer' WHERE is_admin = true")
    op.drop_column("users", "is_admin")
