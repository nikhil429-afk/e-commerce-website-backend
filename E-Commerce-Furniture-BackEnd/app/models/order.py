from pydantic import BaseModel
from typing import Optional


class OrderResponse(BaseModel):
    id: int
    name: str
    user_name: str
    userEmail: str
    category: str
    price: float
    quantity: int
    total_price: float
    in_stock: bool
    created_at: str
    status: str

    class Config:
        from_attributes = True


class OrderStatusUpdate(BaseModel):
    status: str