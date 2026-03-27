"""FastAPI dependency functions (DB session, etc.)."""

import app.database.session as session


get_db = session.get_db
