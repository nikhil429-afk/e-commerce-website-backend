from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional


router = APIRouter(prefix="/owner", tags=["Owner"])

class OwnerDashboardResponse(BaseModel):
    total_users: int
    total_products: int
    total_orders: int


class OwnerProductUpdate(BaseModel):
    name: Optional[str] = None
    image: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    oldPrice: Optional[float] = None
    tag: Optional[str] = None
    description: Optional[str] = None
    in_stock: Optional[bool] = None


class ProductResponse(BaseModel):
    id: int
    name: str
    image: Optional[str] = None
    category: Optional[str] = None
    price: float
    oldPrice: Optional[float] = None
    tag: Optional[str] = None
    description: Optional[str] = None
    in_stock: bool

    class Config:
        from_attributes = True
