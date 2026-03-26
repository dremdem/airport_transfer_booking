"""SQLAlchemy ORM model definitions.

Table implementations are added in Phase 3. This module exposes Base so
alembic/env.py can import target_metadata from the start.
"""

import sqlalchemy.orm

Base = sqlalchemy.orm.declarative_base()
