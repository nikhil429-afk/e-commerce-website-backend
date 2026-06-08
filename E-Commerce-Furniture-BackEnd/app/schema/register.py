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
    password = Column(String(255))
    role = Column(String(50), default="user")
    created_at = Column(DateTime, server_default=func.now())

class UserUpdate(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None