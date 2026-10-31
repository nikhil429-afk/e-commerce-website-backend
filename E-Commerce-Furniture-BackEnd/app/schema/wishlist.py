from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean
from app.core.database import Base


class Wishlist(Base):
    """A wishlist row is a *snapshot* of a product for one user.

    Only user_id and product_id are real foreign keys. The old model also had foreign keys on
    name / image / price / oldPrice / description / in_stock, which made MySQL refuse to edit a
    product while it sat in anyone's wishlist (the 'error when owner updates a product' bug).
    """
    __tablename__ = "wishlist"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(191))
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    image = Column(String(191))
    price = Column(Float)
    oldPrice = Column(Float)
    quantity = Column(Integer, default=1)
    description = Column(String(191))
    in_stock = Column(Boolean)
