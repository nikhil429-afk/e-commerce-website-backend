from sqlalchemy import Column, DateTime, Enum, Integer, String, Float, ForeignKey, Boolean
from app.core.database import Base
from datetime import datetime
from enum import Enum


class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user_name = Column(String(191), ForeignKey("users.username"))
    userEmail = Column(String(191), ForeignKey("users.email"))
    name = Column(String(191))
    category = Column(String(100))
    price = Column(Float, ForeignKey("products.price"))
    quantity = Column(Integer)
    total_price = Column(Float)
    in_stock = Column(Boolean, ForeignKey("products.in_stock"))
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="pending")


class OrderStatus(str, Enum):
    pending = "pending"
    shipped = "shipped"
    delivered = "delivered"
    cancelled = "cancelled"

