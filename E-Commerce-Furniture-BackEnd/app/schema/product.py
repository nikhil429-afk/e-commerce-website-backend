from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean
from pydantic import BaseModel
from app.core.database import Base

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(191))
    image = Column(String(191))
    category = Column(String(100))
    price = Column(Float)
    oldPrice = Column(Float)
    tag = Column(String(100))
    rating = Column(Integer, nullable=True)
    description = Column(String(191))
    in_stock = Column(Boolean, default=True)
    

class Images(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    file_path = Column(String(191))

