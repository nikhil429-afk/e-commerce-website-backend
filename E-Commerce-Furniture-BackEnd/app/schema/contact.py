from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base

class Contact(Base):
    __tablename__ = "contact"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String(100), nullable=True)
    email = Column(String(150), nullable=True)
    phone = Column(String(20), nullable=True)
    subject = Column(String(200), nullable=True)
    appointment_date = Column(String(100), nullable=True)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())