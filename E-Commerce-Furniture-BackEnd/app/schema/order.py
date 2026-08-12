from sqlalchemy import Column, DateTime, Integer, String, Float, ForeignKey, Boolean
from app.core.database import Base
from datetime import datetime


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user_name = Column(String(191))
    userEmail = Column(String(191))
    name = Column(String(191))
    category = Column(String(100))
    price = Column(Float)
    quantity = Column(Integer)
    total_price = Column(Float)
    in_stock = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="pending")

