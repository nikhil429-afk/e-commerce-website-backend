"""Start-up check: tells you plainly when the database is behind the code (forgotten `alembic upgrade head`).

Without it a missing column only shows up later as a confusing "database unavailable" error on login."""
import logging
from sqlalchemy import inspect

from app.core.database import engine
from app.schema.register import User

log = logging.getLogger("schema_check")


def check_user_columns() -> list:
    """Returns the names of columns the code expects on `users` but the database does not have."""
    try:
        have = {c["name"] for c in inspect(engine).get_columns(User.__tablename__)}
    except Exception:
        log.exception("Could not read the users table (is the database running and migrated?)")
        return []
    missing = [c.name for c in User.__table__.columns if c.name not in have]
    if missing:
        log.error(
            "DATABASE IS OUT OF DATE: the users table is missing %s. Stop the server and run:  alembic upgrade head   "
            "Until then login, Google sign-in and profile settings will fail.", ", ".join(missing))
    return missing
