from sqlalchemy import Column, Integer, Float, String, ForeignKey, Boolean
from app.core.database import Base

class Cart(Base):
    __tablename__ = "cart"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    name = Column(String(191))
    image = Column(String(191))
    price = Column(Float)
    oldPrice = Column(Float)
    quantity = Column(Integer, default=1)
    description = Column(String(191))
    in_stock = Column(Boolean, default=True)

