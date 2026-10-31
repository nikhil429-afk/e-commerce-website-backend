"""google login columns, drop wishlist snapshot foreign keys, long product description

Revision ID: a1c0de5afe01
Revises: 0b67efd6a65f
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1c0de5afe01"
down_revision: Union[str, Sequence[str], None] = "0b67efd6a65f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

KEEP_FK_COLUMNS = (["user_id"], ["product_id"])


def _columns(table):
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1) Google sign-in support (idempotent: safe if a column was added by hand)
    user_cols = _columns("users")
    if "auth_provider" not in user_cols:
        op.add_column("users", sa.Column("auth_provider", sa.String(20), nullable=False, server_default="password"))
    if "google_id" not in user_cols:
        op.add_column("users", sa.Column("google_id", sa.String(64), nullable=True))
        op.create_unique_constraint("uq_users_google_id", "users", ["google_id"])
    op.alter_column("users", "password", existing_type=sa.String(255), nullable=True)

    # 2) wishlist: keep only user_id / product_id foreign keys. The others (name, image, price,
    #    oldPrice, description, in_stock -> products.*) blocked editing products.
    for fk in inspector.get_foreign_keys("wishlist"):
        if fk["constrained_columns"] not in KEEP_FK_COLUMNS and fk.get("name"):
            op.drop_constraint(fk["name"], "wishlist", type_="foreignkey")

    # 3) description longer than 191 characters
    op.alter_column("products", "description", existing_type=sa.String(191), type_=sa.Text(), existing_nullable=True)


def downgrade() -> None:
    op.alter_column("products", "description", existing_type=sa.Text(), type_=sa.String(191), existing_nullable=True)
    op.drop_constraint("uq_users_google_id", "users", type_="unique")
    op.drop_column("users", "google_id")
    op.drop_column("users", "auth_provider")
