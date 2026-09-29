"""Replace legacy is_admin flag with AccountType.

Revision ID: 0005_add_account_type
Revises: 0004_remove_unique_indexes
Create Date: 2026-09-28
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_add_account_type"
down_revision = "0004_remove_unique_indexes"
branch_labels = None
depends_on = None


account_type = sa.Enum("organizer", "manager", name="account_type")


def upgrade() -> None:
    bind = op.get_bind()
    account_type.create(bind, checkfirst=True)
    op.add_column("users", sa.Column("account_type", account_type, nullable=True))
    if bind.dialect.name == "postgresql":
        op.execute(
            "UPDATE users SET account_type = CAST(CASE "
            "WHEN is_admin THEN 'organizer' ELSE 'manager' END AS account_type)"
        )
    else:
        op.execute(
            "UPDATE users SET account_type = CASE "
            "WHEN is_admin THEN 'organizer' ELSE 'manager' END"
        )
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "account_type",
            existing_type=account_type,
            existing_nullable=True,
            nullable=False,
            server_default="manager",
        )
        batch_op.drop_column("is_admin")


def downgrade() -> None:
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()))
    if op.get_bind().dialect.name == "postgresql":
        op.execute("UPDATE users SET is_admin = (account_type = 'organizer'::account_type)")
    else:
        op.execute("UPDATE users SET is_admin = (account_type = 'organizer')")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("account_type")
    account_type.drop(op.get_bind(), checkfirst=True)
