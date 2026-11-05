from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class Notification(Base):
    """One message for one user, written whenever the owner does something that concerns them."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    kind = Column(String(40), nullable=False, default="info")       # appointment_accepted, order_updated, ...
    title = Column(String(150), nullable=False)
    message = Column(String(500), nullable=False)
    link = Column(String(120), nullable=True)                       # page to open when the notification is clicked
    is_read = Column(Boolean, nullable=False, default=False, server_default="0")
    created_at = Column(DateTime, server_default=func.now(), index=True)
