"""Drop async_tasks — the batch code review feature was removed

The async_tasks table existed solely to track Celery jobs for
POST /api/v1/tasks/code-review. That feature, its routes, service, repository
and the whole src/worker package are gone, so the table is now unreferenced.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("async_tasks")


def downgrade() -> None:
    # Recreated exactly as 0001 defined it, so downgrading to 0001 is faithful.
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
