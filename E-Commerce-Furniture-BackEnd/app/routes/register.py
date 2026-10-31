from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.schema.register import User
from app.models.register import RegisterRequest
from app.core.database import get_db
from app.core.security import hash_password
from app.core.config import OWNER_EMAIL
import logging
import re

log = logging.getLogger("register")

router = APIRouter(prefix="/register", tags=["register"])


@router.post("/")
def register(data: RegisterRequest, db: Session = Depends(get_db)):

    error = {}
    username_pattern = r"^[a-zA-Z]{3,50}$"

    username = (data.username or "").strip()
    email = (data.email or "").strip().lower()      # always lower case: MySQL emails are case-insensitive

    if not username:
        error["username"] = "Username should not be Empty!"

    elif not re.match(username_pattern, username):
        error["username"] = "Username must be 3-50 letters Only!"

    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    if not email:
        error["email"] = "Email should not be Empty!"

    elif not re.match(email_pattern, email):
        error["email"] = "Invalid Email Format!"

    elif email == OWNER_EMAIL:
        error["email"] = "This Email is reserved and cannot be Registered!"

    # Registration can only ever create normal users. The owner is created from .env at start-up.
    role = "user"

    password_pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d@$#%!]{8,15}$"

    if not data.pwd:
        error["pwd"] = "Password should not be Empty!"

    elif not re.match(password_pattern, data.pwd):
        error["pwd"] = "Password must contain Uppercase, Lowercase, Number. (8-15 Characters)!"

    if data.pwd != data.conf_pwd:
        error["conf_pwd"] = "Passwords didn't Match!"

    if error:
        raise HTTPException(status_code=400, detail=error)

    existing_user = db.query(User).filter(func.lower(User.email) == email).first()

    if existing_user:
        raise HTTPException(status_code=400, detail={"email": "This Email is already Registered!"})

    try:
        new_user = User(username=username, email=email, password=hash_password(data.pwd), role=role, auth_provider="password")
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception:
        db.rollback()
        log.exception("Registration failed")
        raise HTTPException(status_code=500, detail={"error": "Internal Server Error!"})

    return {"message": f"{username} Registration Successful!"}
