from app.core.security import get_current_user, require_owner
from fastapi import APIRouter, Depends, HTTPException
from app.schema.product import Product
from app.core.database import get_db
from sqlalchemy.orm import Session
from app.schema.order import Order
from app.schema.cart import Cart


router = APIRouter(prefix="/orders", tags=["order"])

@router.get("/")
def get_orders(db: Session = Depends(get_db), user: dict = Depends(get_current_user), owner: dict = Depends(require_owner)):
    return db.query(Order).filter(Order.user_id == user.id).all()


@router.post("/checkout")
def create_order(db: Session = Depends(get_db),user: dict = Depends(get_current_user)):

    cart_items = (db.query(Cart).filter(Cart.user_id == user.id).all())

    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    total_amount = 0

    for item in cart_items:

        product = (db.query(Product).filter(Product.id == item.product_id).first())

        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

        if product.in_stock < item.quantity:
            raise HTTPException(status_code=400, detail=f"Only {product.in_stock} units left for {product.name}")

        total_amount += product.price * item.quantity

    try:
        order = Order(user_id=user["id"], total_amount=total_amount, status="pending")

        db.add(order)
        db.flush()
        for item in cart_items:
            product = (db.query(Product).filter(Product.id == item.product_id).first())

            order_item = Order(order_id=order.id, product_id=product.id, quantity=item.quantity, price=product.price)

            db.add(order_item)
            product.in_stock -= item.quantity

        for item in cart_items:
            db.delete(item)

        db.commit()
        db.refresh(order)

        return {"message": "Order created successfully", "order_id": order.id, "total_amount": total_amount}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{order_id}")
def cancel_order(order_id: int, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):

    order = (db.query(Order).filter(Order.id == order_id, Order.user_id == user["id"]).first())

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status in ["shipped", "delivered"]:
        raise HTTPException(status_code=400, detail="Cannot cancel shipped or delivered orders")

    order_items = (db.query(Order).filter(Order.order_id == order.id).all())

    for item in order_items:

        product = (db.query(Product).filter(Product.id == item.product_id).first())
        if product:
            product.in_stock += item.quantity

    order.status = "cancelled"
    db.commit()

    return { "message": "Order cancelled successfully" }

