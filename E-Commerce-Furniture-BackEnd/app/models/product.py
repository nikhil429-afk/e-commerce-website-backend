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



class ProductUpdate(BaseModel):
    name: Optional[str] = None
    image: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    oldPrice: Optional[float] = None
    rating: Optional[int] = None
    tag: Optional[str] = None
    description: Optional[str] = None
    in_stock: Optional[bool] = None


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
