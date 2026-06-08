from pydantic import BaseModel

class OrderResponse(BaseModel):
    id: int
    name: str
    user_name: str
    userEmail: str
    category: str
    price: int
    quantity: int
    total_price: float
    in_stock: bool
    created_at: str
    status: str


class OrderStatusUpdate(BaseModel):
    status: str


    class Config:
        from_attributes = True

