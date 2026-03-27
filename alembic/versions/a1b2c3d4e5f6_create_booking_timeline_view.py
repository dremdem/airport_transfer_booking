"""create booking_timeline_view

Revision ID: a1b2c3d4e5f6
Revises: 73590898a60e
Create Date: 2026-03-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '73590898a60e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE VIEW booking_timeline_view AS
        SELECT
            b.id             AS booking_id,
            b.passenger_name,
            b.flight_number,
            b.pickup_time,
            b.pickup_location,
            b.dropoff_location,
            b.status         AS current_status,
            h.id             AS history_id,
            h.old_status,
            h.new_status,
            h.created_at     AS transitioned_at
        FROM booking b
        INNER JOIN booking_status_history h ON h.booking_id = b.id
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS booking_timeline_view")
