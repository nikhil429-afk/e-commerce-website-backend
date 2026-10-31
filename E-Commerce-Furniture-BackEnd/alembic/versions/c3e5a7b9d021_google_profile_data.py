"""store the Google profile picture and the last login time

Revision ID: c3e5a7b9d021
Revises: 8ca3b7ca8b5d
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3e5a7b9d021"
down_revision: Union[str, Sequence[str], None] = "8ca3b7ca8b5d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("users")}
    if "avatar_url" not in cols:
        op.add_column("users", sa.Column("avatar_url", sa.String(500), nullable=True))
    if "last_login_at" not in cols:
        op.add_column("users", sa.Column("last_login_at", sa.DateTime(), nullable=True))
    # Accounts that have both a password and a linked Google account are marked "both".
    op.execute("UPDATE users SET auth_provider = 'both' WHERE google_id IS NOT NULL AND password IS NOT NULL AND password <> ''")


def downgrade() -> None:
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "avatar_url")
