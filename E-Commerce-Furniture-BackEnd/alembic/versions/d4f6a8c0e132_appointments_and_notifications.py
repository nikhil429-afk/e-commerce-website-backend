"""appointment decisions (accept / decline / change date) and the notifications table

Revision ID: d4f6a8c0e132
Revises: c3e5a7b9d021
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4f6a8c0e132"
down_revision: Union[str, Sequence[str], None] = "c3e5a7b9d021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())

    cols = {c["name"] for c in insp.get_columns("contact")}
    if "status" not in cols:
        op.add_column("contact", sa.Column("status", sa.String(20), nullable=False, server_default="pending"))
    if "original_date" not in cols:
        op.add_column("contact", sa.Column("original_date", sa.String(100), nullable=True))
    if "owner_note" not in cols:
        op.add_column("contact", sa.Column("owner_note", sa.String(300), nullable=True))
    if "decided_at" not in cols:
        op.add_column("contact", sa.Column("decided_at", sa.DateTime(), nullable=True))

    if "notifications" not in insp.get_table_names():
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("kind", sa.String(40), nullable=False),
            sa.Column("title", sa.String(150), nullable=False),
            sa.Column("message", sa.String(500), nullable=False),
            sa.Column("link", sa.String(120), nullable=True),
            sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )
        op.create_index("ix_notifications_id", "notifications", ["id"])
        op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
        op.create_index("ix_notifications_created_at", "notifications", ["created_at"])


def downgrade() -> None:
    op.drop_table("notifications")
    for col in ("decided_at", "owner_note", "original_date", "status"):
        op.drop_column("contact", col)
