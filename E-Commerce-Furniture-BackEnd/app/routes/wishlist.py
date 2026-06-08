from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schema.wishlist import Wishlist
from app.schema.product import Product
from app.core.security import get_current_user

router = APIRouter(prefix="/wishlist", tags=["wishlist"])


@router.get("/")
def get_wishlist(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(Wishlist).filter(Wishlist.user_id == user.id).all()


@router.post("/{item_id}")
def add_to_wishlist(item_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    existing = db.query(Wishlist).filter(Wishlist.product_id == item_id, Wishlist.user_id == user.id).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Item Already in Wishlist")

    product = db.query(Product).filter(Product.id == item_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    new_item = Wishlist(
        user_id = user.id,
        name = product.name,
        product_id = item_id,
        image = product.image,
        price = product.price,
        oldPrice = product.oldPrice,
        description = product.description,
        in_stock = product.in_stock,
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


@router.delete("/{item_id}")
def remove_from_wishlist(item_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    item = db.query(Wishlist).filter(Wishlist.id == item_id, Wishlist.user_id == user.id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found in wishlist")
    
    db.delete(item)
    db.commit()
    return {"message": "Item removed from Wishlist"}