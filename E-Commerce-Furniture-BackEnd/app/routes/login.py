import re
import time
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.schema.register import User
from app.core.security import create_access_token, verify_password
from app.core.config import OWNER_EMAIL, GOOGLE_CLIENT_ID

log = logging.getLogger("login")

router = APIRouter(prefix="/login", tags=["Login"])

# The PC running the server is allowed to be this many seconds out of sync with Google's clock.
# Without this, a clock that is only a few seconds slow rejects a perfectly good Google token
# ("Token used too early"), which is a very common cause of "Google login fails" on Windows.
CLOCK_SKEW_SECONDS = 60


class LoginRequest(BaseModel):
    email: EmailStr
    pwd: str


class GoogleLoginRequest(BaseModel):
    credential: str          # the Google ID token returned by the "Sign in with Google" button


def _session_payload(user: User) -> dict:
    """The same response shape for password login and Google login."""
    access_token = create_access_token(
        {"id": user.id, "username": user.username, "email": user.email, "role": user.role}
    )
    return {
        "message": "Login Successful",
        "access_token": access_token,
        "role": user.role,
        "user": {"id": user.id, "username": user.username, "email": user.email, "role": user.role,
                 "phone": user.phone, "address": user.address, "avatar_url": user.avatar_url},
    }


@router.post("/")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    # Owner and normal users go through the same path. The owner row is created at start-up
    # from .env (see core/owner_seed.py); its role is read from the database.
    email = data.email.strip().lower()
    user = db.query(User).filter(func.lower(User.email) == email).first()

    if not user:
        raise HTTPException(status_code=400, detail={"email": "User not Found"})

    if not user.password:
        raise HTTPException(status_code=400, detail={"email": "This account uses Google sign-in. Use the Google button."})

    if not verify_password(data.pwd, user.password):
        raise HTTPException(status_code=401, detail={"pwd": "Wrong Password"})

    user.last_login_at = datetime.utcnow()
    db.commit()
    return _session_payload(user)


# ---------------------------------------------------------------------------------------------
# Google sign-in / sign-up
# ---------------------------------------------------------------------------------------------
_cert_cache: dict = {}


def _google_request():
    """google-auth transport with a short timeout (so a blocked network fails fast instead of hanging
    for two minutes) and a small cache of Google's public certificates (so we don't download them on
    every single login)."""
    from google.auth.transport import requests as g_requests

    class _Request(g_requests.Request):
        def __call__(self, url, method="GET", body=None, headers=None, timeout=10, **kwargs):
            now = time.time()
            hit = _cert_cache.get(url)
            if method == "GET" and hit and hit[0] > now:
                return hit[1]
            response = super().__call__(url, method=method, body=body, headers=headers, timeout=timeout, **kwargs)
            if method == "GET" and getattr(response, "status", None) == 200:
                _cert_cache[url] = (now + 600, response)
            return response

    return _Request()


def _verify_google_token(credential: str) -> dict:
    """Verify the Google ID token and turn every failure into a clear, actionable message."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured on the server (GOOGLE_CLIENT_ID is missing in the backend .env).")

    try:
        from google.oauth2 import id_token
        from google.auth import exceptions as g_exc
    except ImportError:
        log.exception("google-auth is not installed")
        raise HTTPException(status_code=503, detail="The server is missing the google-auth package. Run: pip install google-auth requests")

    try:
        return id_token.verify_oauth2_token(credential, _google_request(), GOOGLE_CLIENT_ID,
                                            clock_skew_in_seconds=CLOCK_SKEW_SECONDS)
    except g_exc.TransportError:
        log.exception("Could not download Google's public keys")
        raise HTTPException(status_code=503, detail="The server could not reach Google to check your sign-in. Check the internet connection, firewall or proxy of the machine running the backend.")
    except ValueError as e:
        reason = str(e)
        log.warning("Google token rejected: %s", reason)
        low = reason.lower()
        if "wrong recipient" in low or "audience" in low:
            raise HTTPException(status_code=401, detail="The Google Client ID used by the website does not match the one in the backend .env. Make sure VITE_GOOGLE_CLIENT_ID and GOOGLE_CLIENT_ID are identical.")
        if "too early" in low:
            raise HTTPException(status_code=401, detail="Your computer's clock is out of sync with Google's. Turn on automatic date & time (and sync it), then try again.")
        if "expired" in low:
            raise HTTPException(status_code=401, detail="That Google sign-in expired. Please click the Google button again.")
        raise HTTPException(status_code=401, detail="Google could not verify this sign-in. Please try again.")
    except Exception:
        log.exception("Unexpected error while verifying the Google token")
        raise HTTPException(status_code=502, detail="Could not verify the Google sign-in right now. Please try again.")


def _display_name(info: dict, email: str) -> str:
    """A clean display name (letters, spaces, . ' -) of 2-50 characters; falls back to the email name."""
    for candidate in (info.get("name"), info.get("given_name"), email.split("@")[0]):
        cleaned = re.sub(r"[^A-Za-z .'-]", " ", candidate or "")
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" .'-")
        if len(cleaned) >= 2:
            return cleaned[:50]
    return "Guest"


def _clean_picture(url) -> str | None:
    url = (url or "").strip()
    return url[:500] if url.startswith("https://") else None


@router.get("/google/status")
def google_status():
    """Lets the website check that frontend and backend use the same Google Client ID."""
    return {"configured": bool(GOOGLE_CLIENT_ID), "client_id": GOOGLE_CLIENT_ID or None}


@router.post("/google")
def google_login(data: GoogleLoginRequest, db: Session = Depends(get_db)):
    """Log in OR sign up with Google. One endpoint serves both buttons."""
    info = _verify_google_token(data.credential)

    email = (info.get("email") or "").strip().lower()
    google_id = info.get("sub")
    if not email or not google_id:
        raise HTTPException(status_code=401, detail="Google did not share your email address.")
    if not info.get("email_verified"):
        raise HTTPException(status_code=401, detail="Your Google email address is not verified.")

    picture = _clean_picture(info.get("picture"))

    def find_user():
        by_google = db.query(User).filter(User.google_id == google_id).first()
        return by_google or db.query(User).filter(func.lower(User.email) == email).first()

    user = find_user()

    if email == OWNER_EMAIL or (user is not None and user.role == "owner"):
        raise HTTPException(status_code=403, detail="The owner account must sign in with email and password.")

    try:
        if user is None:
            # ---- sign up
            user = User(username=_display_name(info, email), email=email, password=None, role="user",
                        auth_provider="google", google_id=google_id, avatar_url=picture, last_login_at=datetime.utcnow())
            db.add(user)
            db.commit()
        else:
            # ---- log in (and link the Google account if this email already had a password account)
            if user.google_id and user.google_id != google_id:
                raise HTTPException(status_code=401, detail="This email is linked to a different Google account.")
            if not user.google_id:
                user.google_id = google_id
            user.auth_provider = "both" if user.password else "google"
            if picture:
                user.avatar_url = picture
            user.last_login_at = datetime.utcnow()
            db.commit()
        db.refresh(user)
    except HTTPException:
        raise
    except IntegrityError:
        # Two sign-ins for the same new account at the same moment: the other one won, use its row.
        db.rollback()
        user = find_user()
        if user is None:
            log.exception("Could not create the Google user")
            raise HTTPException(status_code=500, detail="Could not create your account. Please try again.")
        if user.role == "owner":
            raise HTTPException(status_code=403, detail="The owner account must sign in with email and password.")
    except Exception:
        db.rollback()
        log.exception("Saving the Google user failed")
        raise HTTPException(status_code=500, detail="Could not save your account. Please try again.")

    return _session_payload(user)
