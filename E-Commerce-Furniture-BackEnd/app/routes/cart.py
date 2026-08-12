from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schema.cart import Cart
from app.core.security import get_current_user
from app.schema.product import Product

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("/")
def get_cart(db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        return db.query(Cart).filter(Cart.user_id == user.id).all()
    except:
        raise HTTPException(status_code=500, detail="Could not fetch cart items")


@router.put("/{item_id}")
def add_to_cart(item_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    existing = db.query(Cart).filter(Cart.product_id == item_id, Cart.user_id == user.id).first()
    if existing:
        existing.quantity += 1
        db.commit()
        db.refresh(existing)
        return existing

    product = db.query(Product).filter(Product.id == item_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    new_item = Cart(
        product_id  = item_id,
        user_id = user.id,
        name = product.name,
        image = product.image,
        price = product.price,
        oldPrice = product.oldPrice,
        description = product.description,
        in_stock = product.in_stock,
        quantity = 1,
    )
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


@router.delete("/delete/{item_id}")
def remove_from_cart(item_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        item = db.query(Cart).filter(Cart.id == item_id, Cart.user_id == user.id).first()

        if not item:
            raise HTTPException(status_code=404, detail="Item Not Found in Cart")
        db.delete(item)
        db.commit()
        return {"message": "Item Removed from Cart"}
    except:
        raise HTTPException(status_code=500, detail="Unable to Delete Item from Cart")


@router.patch("/increase/{item_id}")
def increase_quantity(item_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    cart_item = db.query(Cart).filter(Cart.id == item_id, Cart.user_id == user.id).first()
    if not cart_item:
        raise HTTPException(status_code=404, detail="Item Not Found in Cart")
    if cart_item.quantity >= 8:
        raise HTTPException(status_code=400, detail="Maximum Quantity Limit is 8")
    cart_item.quantity += 1
    db.commit()
    db.refresh(cart_item)
    return cart_item


@router.patch("/decrease/{item_id}")
def decrease_quantity(item_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    cart_item = db.query(Cart).filter(Cart.id == item_id, Cart.user_id == user.id).first()
    if not cart_item:
        raise HTTPException(status_code=404, detail="Item Not Found in Cart")
    if cart_item.quantity <= 1:
        raise HTTPException(status_code=400, detail="Quantity Cannot go Below 1")
    cart_item.quantity -= 1
    db.commit()
    db.refresh(cart_item)
    return cart_item
