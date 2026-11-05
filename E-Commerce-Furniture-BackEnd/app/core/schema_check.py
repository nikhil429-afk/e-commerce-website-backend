"""Start-up check: tells you plainly when the database is behind the code (forgotten `alembic upgrade head`).

Without it a missing column only shows up later as a confusing "database unavailable" error on login."""
import logging
from sqlalchemy import inspect, text

from app.core.database import engine
from app.schema.register import User
from app.schema.contact import Contact
from app.schema.notification import Notification

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


def ensure_appointment_and_notification_schema() -> None:
    """Self-heal for the appointment decisions + notifications feature (same changes as the alembic migration
    d4f6a8c0e132). Safe to run on every start: it only adds what is missing."""
    try:
        insp = inspect(engine)
        if Notification.__tablename__ not in insp.get_table_names():
            Notification.__table__.create(bind=engine, checkfirst=True)
            log.info("Created the notifications table")
        have = {c["name"] for c in insp.get_columns(Contact.__tablename__)}
        ddl = {
            "status": "ALTER TABLE contact ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'pending'",
            "original_date": "ALTER TABLE contact ADD COLUMN original_date VARCHAR(100) NULL",
            "owner_note": "ALTER TABLE contact ADD COLUMN owner_note VARCHAR(300) NULL",
            "decided_at": "ALTER TABLE contact ADD COLUMN decided_at DATETIME NULL",
        }
        for col, stmt in ddl.items():
            if col not in have:
                with engine.begin() as conn:
                    conn.execute(text(stmt))
                log.info("Added contact.%s", col)
    except Exception:
        log.exception("Could not verify the appointment/notification tables. Run:  alembic upgrade head")
