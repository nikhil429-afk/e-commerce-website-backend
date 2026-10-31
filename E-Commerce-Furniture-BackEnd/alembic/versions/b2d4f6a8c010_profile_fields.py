"""profile settings: phone number and address on users

Revision ID: b2d4f6a8c010
Revises: a1c0de5afe01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2d4f6a8c010"
down_revision: Union[str, Sequence[str], None] = "a1c0de5afe01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("users")}
    if "phone" not in cols:
        op.add_column("users", sa.Column("phone", sa.String(30), nullable=True))
    if "address" not in cols:
        op.add_column("users", sa.Column("address", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "address")
    op.drop_column("users", "phone")
