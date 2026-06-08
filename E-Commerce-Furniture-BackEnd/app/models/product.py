from pydantic import BaseModel
from typing import Optional


class ProductResponse(BaseModel):
    id: int
    name: str
    image: Optional[str] = None
    category: Optional[str] = None
    price: float
    oldPrice: Optional[float] = None
    tag: Optional[str] = None
    rating: int
    description: Optional[str] = None
    in_stock: bool

    class Config:
        from_attributes = True


class CreateProduct(BaseModel):
    name: str
    category: str
    image: Optional[str] = None
    price: float
    oldPrice: float
    rating: int
    tag: str
    description: str
    in_stock: bool = True


class ImageBase(BaseModel):
    id: int
    product_id: int
    category: str
    file_path: str
