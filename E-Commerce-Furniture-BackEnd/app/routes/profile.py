import logging
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import OWNER_EMAIL
from app.core.database import get_db
from app.core.security import create_access_token, get_current_user, hash_password, verify_password
from app.schema.register import User

log = logging.getLogger("profile")

router = APIRouter(prefix="/profile", tags=["Profile"])

NAME_RE = re.compile(r"^[A-Za-z][A-Za-z .'-]{1,49}$")
EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
PHONE_RE = re.compile(r"^\+?[0-9][0-9 ()-]{6,19}$")
PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d@$#%!]{8,15}$")


class ProfileUpdate(BaseModel):
    username: Optional[str] = Field(default=None, max_length=100)
    email: Optional[str] = Field(default=None, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=30)
    address: Optional[str] = Field(default=None, max_length=255)


class PasswordChange(BaseModel):
    current_password: Optional[str] = None      # not needed for Google-only accounts that have no password yet
    new_password: str
    confirm_password: str


def _public(user: User) -> dict:
    return {
        "id": user.id, "username": user.username, "email": user.email, "role": user.role,
        "phone": user.phone or "", "address": user.address or "",
        "auth_provider": user.auth_provider or "password",
        "google_linked": bool(user.google_id),
        "avatar_url": user.avatar_url or "",
        "has_password": bool(user.password),
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _token(user: User) -> str:
    return create_access_token({"id": user.id, "username": user.username, "email": user.email, "role": user.role})


@router.get("")
def get_profile(user: User = Depends(get_current_user)):
    return _public(user)


@router.patch("")
def update_profile(data: ProfileUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    errors = {}
    fields = data.model_fields_set

    if "username" in fields:
        name = (data.username or "").strip()
        if not NAME_RE.match(name):
            errors["username"] = "Name must be 2-50 characters (letters, spaces, . ' - only)."
    if "email" in fields:
        email = (data.email or "").strip().lower()
        if not EMAIL_RE.match(email):
            errors["email"] = "Enter a valid email address."
        elif email != (user.email or "").lower():
            if user.google_id:
                errors["email"] = "This account is linked to Google, so its email can't be changed here."
            elif email == OWNER_EMAIL and user.role != "owner":
                errors["email"] = "This email is reserved."
            elif db.query(User).filter(func.lower(User.email) == email, User.id != user.id).first():
                errors["email"] = "This email is already used by another account."
    if "phone" in fields:
        phone = (data.phone or "").strip()
        if phone and not PHONE_RE.match(phone):
            errors["phone"] = "Enter a valid phone number (digits, +, spaces, brackets, dashes; 7-20 characters)."
    if "address" in fields and len((data.address or "").strip()) > 255:
        errors["address"] = "Address is too long (max 255 characters)."

    if errors:
        raise HTTPException(status_code=400, detail=errors)

    try:
        if "username" in fields: user.username = (data.username or "").strip()
        if "email" in fields: user.email = (data.email or "").strip().lower()
        if "phone" in fields: user.phone = (data.phone or "").strip() or None
        if "address" in fields: user.address = (data.address or "").strip() or None
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        log.exception("Profile update failed")
        raise HTTPException(status_code=500, detail="Could not save your profile. Nothing was changed.")

    return {"message": "Profile updated successfully", "user": _public(user), "access_token": _token(user)}


@router.post("/password")
def change_password(data: PasswordChange, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    errors = {}

    if user.password:
        if not data.current_password:
            errors["current_password"] = "Enter your current password."
        elif not verify_password(data.current_password, user.password):
            errors["current_password"] = "Current password is wrong."

    if not PASSWORD_RE.match(data.new_password or ""):
        errors["new_password"] = "Use 8-15 characters with an uppercase letter, a lowercase letter and a number."
    elif user.password and data.current_password and data.new_password == data.current_password:
        errors["new_password"] = "The new password must be different from the current one."

    if data.new_password != data.confirm_password:
        errors["confirm_password"] = "Passwords didn't match."

    if errors:
        raise HTTPException(status_code=400, detail=errors)

    try:
        user.password = hash_password(data.new_password)
        user.auth_provider = "both" if user.google_id else "password"
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        log.exception("Password change failed")
        raise HTTPException(status_code=500, detail="Could not change the password. Nothing was changed.")

    return {"message": "Password changed successfully", "user": _public(user), "access_token": _token(user)}
