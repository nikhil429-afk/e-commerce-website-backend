from pydantic import BaseModel


class WishlistResponse(BaseModel):
    id: int
    user_id: int
    product_id: int
    image: str
    price: int
    oldPrice: int
    quantity: int
    description: str
    in_stock: bool

    class Config:
        from_attributes = True

