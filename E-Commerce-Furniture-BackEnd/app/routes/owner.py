from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.schema.register import User
from app.schema.product import Product
from app.models.product import CreateProduct
from app.schema.order import Order
from app.models.order import OrderStatusUpdate
from app.schema.contact import Contact
from app.core.database import get_db
from app.core.security import require_owner

router = APIRouter(prefix="/owner", tags=["Owner"])


class UserUpdate(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


@router.get("/users")
def get_all_users(db: Session = Depends(get_db), owner=Depends(require_owner)):
    users = db.query(User).all()
    return [{ "id": u.id, "username": u.username, "email": u.email, "role": u.role, }
        for u in users
    ]


@router.patch("/users/{user_id}")
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db), owner=Depends(require_owner)):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.username is not None:
        user.username = data.username
    if data.role is not None:
        user.role = data.role

    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username, "email": user.email, "role": user.role, }


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), owner=Depends(require_owner)):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}


@router.get("/products")
def get_all_products(db: Session = Depends(get_db), owner=Depends(require_owner)):
    products = db.query(Product).all()
    return [_product_dict(p) for p in products]


@router.get("/contact")
def get_all_contacts(db: Session = Depends(get_db), owner=Depends(require_owner)):
    contacts = db.query(Contact).all()
    return [_contact_dict(c) for c in contacts]


@router.get("/appointments")
def get_all_appointments(db: Session = Depends(get_db), owner=Depends(require_owner)):
    appointments = db.query(Contact).filter(Contact.subject == "Showroom Visit").all()
    return [appointment_dict(a) for a in appointments]


@router.post("/products")
def create_product(data: CreateProduct, db: Session = Depends(get_db), owner=Depends(require_owner)):
    new_product = Product(
        name = data.name,
        image = data.image,
        category = data.category,
        price = data.price,
        oldPrice = data.oldPrice,
        rating = data.rating,
        tag = data.tag,
        description = data.description,
        in_stock = data.in_stock,
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return _product_dict(new_product)


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


@router.patch("/products/{product_id}")
def update_product(product_id: int, data: ProductUpdate, db: Session = Depends(get_db), owner=Depends(require_owner)):
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if data.name is not None: product.name = data.name
    if data.image is not None: product.image = data.image
    if data.category is not None: product.category = data.category
    if data.price is not None: product.price = data.price
    if data.oldPrice is not None: product.oldPrice = data.oldPrice
    if data.rating is not None: product.rating = data.rating
    if data.tag is not None: product.tag = data.tag
    if data.description is not None: product.description = data.description
    if data.in_stock is not None: product.in_stock = data.in_stock

    db.commit()
    db.refresh(product)
    return _product_dict(product)


@router.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), owner=Depends(require_owner)):
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(product)
    db.commit()
    return {"message": "Product deleted successfully"}


@router.get("/orders")
def get_all_orders(db: Session = Depends(get_db), owner=Depends(require_owner)):
    orders = db.query(Order).all()
    return [_order_dict(o) for o in orders]


@router.patch("/orders/{order_id}")
def update_order_status(order_id: int, data: OrderStatusUpdate, db: Session = Depends(get_db), owner=Depends(require_owner)):
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = data.status

    db.commit()
    db.refresh(order)

    return { "message": f"Order status updated to {data.status}", "order": _order_dict(order)}



def _product_dict(p) -> dict:
    return {
        "id": p.id,
        "name": p.name or "",
        "image": p.image or "",
        "category": p.category or "",
        "price": p.price or 0,
        "oldPrice": p.oldPrice or 0,
        "rating": p.rating or 0,
        "tag": p.tag or "",
        "description": p.description or "",
        "in_stock": p.in_stock if p.in_stock is not None else True,
    }


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
        "status": "pending" if (o.in_stock is None or o.in_stock) else "shipped",
    }


def _contact_dict(c) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "email": c.email,
        "phone": c.phone,
        "subject": c.subject,
        "message": c.message,
    }


def appointment_dict(c) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "email": c.email,
        "phone": c.phone,
        "appointment_date": c.appointment_date,
        "message": c.message,
    }

