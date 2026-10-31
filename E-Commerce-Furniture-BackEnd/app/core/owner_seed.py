"""Makes sure an owner account exists.

How "owner" is decided:
  * the `users.role` column is "owner" or "user";
  * every protected owner route checks that DB column (require_owner in security.py);
  * registration can never create an owner, and Google sign-in can never log into an owner account.

The OWNER_EMAIL / OWNER_PASSWORD pair in .env creates the FIRST owner. After that the owner manages
their own name / email / password in Profile Settings and those changes survive restarts.
Forgot the owner password? Set OWNER_FORCE_RESET=1 in .env, restart once, then remove it - the owner
row is reset to the .env email and password.
"""
import logging
import os
from sqlalchemy import func

from app.core.config import OWNER_EMAIL, OWNER_NAME, OWNER_PASSWORD
from app.core.database import LocalSession
from app.core.security import hash_password, verify_password
from app.schema.register import User

log = logging.getLogger("owner_seed")


def seed_owner() -> None:
    if not OWNER_EMAIL or not OWNER_PASSWORD:
        log.warning("OWNER_EMAIL / OWNER_PASSWORD not set - no owner account will be created.")
        return

    force = os.getenv("OWNER_FORCE_RESET", "").strip().lower() in ("1", "true", "yes")

    db = LocalSession()
    try:
        by_env_email = db.query(User).filter(func.lower(User.email) == OWNER_EMAIL).first()
        existing_owner = db.query(User).filter(User.role == "owner").order_by(User.id).first()

        if by_env_email is None and existing_owner is None:
            db.add(User(username=OWNER_NAME, email=OWNER_EMAIL, password=hash_password(OWNER_PASSWORD),
                        role="owner", auth_provider="password"))
            log.info("Owner account created for %s", OWNER_EMAIL)

        elif by_env_email is not None and by_env_email.role != "owner":
            # A row with the owner's email exists but is not the owner (e.g. registered before the fix): adopt it.
            by_env_email.email = OWNER_EMAIL
            by_env_email.role = "owner"
            by_env_email.auth_provider = "password"
            by_env_email.password = hash_password(OWNER_PASSWORD)

        elif force:
            target = by_env_email or existing_owner
            target.email = OWNER_EMAIL
            target.role = "owner"
            target.auth_provider = "password"
            if not verify_password(OWNER_PASSWORD, target.password):
                target.password = hash_password(OWNER_PASSWORD)
            log.warning("OWNER_FORCE_RESET applied - remove it from .env now.")

        db.commit()
    except Exception:
        db.rollback()
        log.exception("Could not seed the owner account (has `alembic upgrade head` been run?)")
    finally:
        db.close()
