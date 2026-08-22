"""Single user — drop chat_sessions.user_id and the users table

The platform no longer has per-user identity: authentication was removed and
sessions are global to the single local user. chat_sessions.user_id and the
users table it referenced are therefore unreferenced.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Postgres drops a column's dependent index and FK constraint with the
    # column itself, so no explicit drop_index is needed (and naming one would
    # risk a mismatch with whatever 0001's inline index=True produced).
    op.drop_column("chat_sessions", "user_id")
    op.drop_table("users")


def downgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("api_key", sa.String(100), nullable=False, unique=True, index=True),
        sa.Column("created_at", sa.DateTime),
    )
    # Nullable on the way back: existing rows have no user to attribute them to.
    op.add_column(
        "chat_sessions",
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])
