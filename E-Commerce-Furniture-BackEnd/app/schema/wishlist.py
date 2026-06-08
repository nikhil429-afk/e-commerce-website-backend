from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean
from app.core.database import Base

class Wishlist(Base):
    __tablename__ = "wishlist"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(191), ForeignKey("products.name"))
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    image = Column(String(191), ForeignKey("products.image"))
    price = Column(Float, ForeignKey("products.price"))
    oldPrice = Column(Float, ForeignKey("products.oldPrice"))
    quantity = Column(Integer, default=1)
    description = Column(String(191), ForeignKey("products.description"))
    in_stock = Column(Boolean, ForeignKey("products.in_stock"))
    