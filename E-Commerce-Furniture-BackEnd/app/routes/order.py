from fastapi import APIRouter, Depends, HTTPException
import logging
from app.core.security import get_current_user
from app.schema.product import Product
from app.core.database import get_db
from sqlalchemy.orm import Session
from app.schema.order import Order
from app.schema.cart import Cart
from app.schema.register import User

router = APIRouter(prefix="/orders", tags=["order"])


@router.get("/")
def get_orders(db: Session = Depends(get_db), user=Depends(get_current_user)):
    orders = db.query(Order).filter(Order.user_id == user.id).all()
    return [_order_dict(o) for o in orders]


@router.post("/checkout")
def create_order(db: Session = Depends(get_db), user=Depends(get_current_user)):
    cart_items = db.query(Cart).filter(Cart.user_id == user.id).all()

    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    for item in cart_items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

    try:
        order_ids = []

        for item in cart_items:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            total_price = product.price * item.quantity

            order = Order(
                user_id=user.id,
                user_name=user.username,
                userEmail=user.email,
                name=item.name,
                category=product.category,
                price=item.price,
                quantity=item.quantity,
                total_price=total_price,
                in_stock=item.in_stock,
                status="pending",
            )
            db.add(order)
            db.flush()
            order_ids.append(order.id)

        for item in cart_items:
            db.delete(item)

        db.commit()

        return {"message": "Order placed successfully", "order_ids": order_ids, "order_id": order_ids[0] if order_ids else None,}

    except Exception as e:
        db.rollback()
        logging.getLogger("orders").exception("Order failed")
        raise HTTPException(status_code=500, detail="Could not place the order. Nothing was charged or changed.")


@router.post("/checkout/{item_id}")
def checkout_single_item(item_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    cart_item = db.query(Cart).filter(Cart.id == item_id, Cart.user_id == user.id).first()

    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    product = db.query(Product).filter(Product.id == cart_item.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    try:
        total_price = cart_item.price * cart_item.quantity

        order = Order(
            user_id=user.id,
            user_name=user.username,
            userEmail=user.email,
            name=cart_item.name,
            category=product.category,
            price=cart_item.price,
            quantity=cart_item.quantity,
            total_price=total_price,
            in_stock=cart_item.in_stock,
            status="pending",
        )
        db.add(order)
        db.flush()

        db.delete(cart_item)
        db.commit()

        return {"message": "Item ordered successfully", "order_id": order.id}

    except Exception as e:
        db.rollback()
        logging.getLogger("orders").exception("Order failed")
        raise HTTPException(status_code=500, detail="Could not place the order. Nothing was charged or changed.")


@router.delete("/{order_id}")
def cancel_order(order_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == user.id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status in ["shipped", "delivered"]:
        raise HTTPException(status_code=400, detail="Cannot cancel shipped or delivered orders")

    order.status = "cancelled"
    db.commit()

    return {"message": "Order cancelled successfully"}


def _order_dict(o) -> dict:
    return {
        "id": o.id,
        "user_name": o.user_name or "",
        "userEmail": o.userEmail or "",
        "name": o.name or "",
        "category": o.category or "",
        "price": o.price or 0,
        "quantity": o.quantity or 1,
        "total_price": o.total_price or 0,
        "in_stock": o.in_stock if o.in_stock is not None else True,
        "status": o.status or "pending",
        "created_at": str(o.created_at) if o.created_at else "",
    }