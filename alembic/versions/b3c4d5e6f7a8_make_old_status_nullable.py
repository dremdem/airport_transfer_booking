"""make booking_status_history.old_status nullable

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-03-27 15:00:00.000000

old_status is NULL for the creation history row that BookingRepository.create()
inserts to represent the initial state of every booking.  The architecture doc
already documented this intent; the original migration incorrectly set NOT NULL.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b3c4d5e6f7a8'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'booking_status_history',
        'old_status',
        existing_type=sa.String(length=20),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        'booking_status_history',
        'old_status',
        existing_type=sa.String(length=20),
        nullable=False,
    )
