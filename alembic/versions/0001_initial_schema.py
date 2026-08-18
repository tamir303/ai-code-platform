"""Initial schema — users, chat_sessions, chat_messages, async_tasks

Revision ID: 0001
Revises:
Create Date: 2026-08-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(50), unique=True, nullable=False, index=True),
        sa.Column("api_key", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("created_at", sa.DateTime),
    )

    # --- chat_sessions ---
    op.create_table(
        "chat_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime),
    )

    # --- chat_messages ---
    op.create_table(
        "chat_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("chat_sessions.id"), nullable=False, index=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime),
    )

    # --- async_tasks ---
    op.create_table(
        "async_tasks",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("task_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), server_default="PENDING"),
        sa.Column("result", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime),
    )


def downgrade() -> None:
    op.drop_table("async_tasks")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("users")
