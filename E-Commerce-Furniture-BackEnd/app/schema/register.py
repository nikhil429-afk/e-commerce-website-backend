from sqlalchemy import Column, Integer, String, DateTime
from app.core.database import Base
from sqlalchemy.sql import func
from pydantic import BaseModel
from typing import Optional


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=True)          # NULL for Google-only accounts
    role = Column(String(50), default="user")
    phone = Column(String(30), nullable=True)
    address = Column(String(255), nullable=True)
    auth_provider = Column(String(20), nullable=False, default="password", server_default="password")
    google_id = Column(String(64), unique=True, nullable=True)
    avatar_url = Column(String(500), nullable=True)          # profile picture from Google
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class UserUpdate(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
