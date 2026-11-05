from fastapi import APIRouter, Depends, HTTPException
from datetime import date, datetime
from sqlalchemy.orm import Session
from typing import Optional, Literal
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from app.schema.register import User
from app.schema.product import Product, Images
from app.schema.cart import Cart
from app.schema.wishlist import Wishlist
from app.models.product import CreateProduct, ProductUpdate
from app.schema.order import Order
from app.models.order import OrderStatusUpdate
from app.schema.contact import Contact
from app.core.database import get_db
from app.core.security import require_owner
from app.core.notify import notify

router = APIRouter(prefix="/owner", tags=["Owner"])


class UserUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=1, max_length=100)
    role: Optional[Literal["user", "owner"]] = None


@router.get("/users")
def get_all_users(db: Session = Depends(get_db), owner=Depends(require_owner)):
    users = db.query(User).all()
    return [[u.id, u.username, u.email, u.role,] for u in users ]


@router.patch("/users/{user_id}")
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db), owner=Depends(require_owner)):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if data.role is not None and user.id == owner.id and data.role != "owner":
        raise HTTPException(status_code=400, detail="You cannot remove your own owner access.")

    changes = []
    if data.username is not None and data.username.strip() != user.username:
        changes.append(f"your name was changed to {data.username.strip()}")
    if data.role is not None and data.role != user.role:
        changes.append(f"your account type is now {data.role}")

    if data.username is not None:
        user.username = data.username.strip()
    if data.role is not None:
        user.role = data.role

    db.commit()
    db.refresh(user)
    if changes and user.id != owner.id:
        notify(db, user.id, "account_updated", "Account updated", "The store owner updated your account: " + " and ".join(changes) + ".", "/profile")
    return [ user.id, user.username, user.email, user.role, ]


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), owner=Depends(require_owner)):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == owner.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own owner account.")

    try:
        db.query(Cart).filter(Cart.user_id == user.id).delete()
        db.query(Wishlist).filter(Wishlist.user_id == user.id).delete()
        db.delete(user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="This user still has orders or messages, so the account cannot be deleted.")
    return {"message": "User deleted successfully"}


@router.get("/products")
def get_all_products(db: Session = Depends(get_db), owner=Depends(require_owner)):
    products = db.query(Product).all()
    return [
        [
            p.id,
            p.name,
            p.image,
            p.category,
            p.price,
            p.oldPrice,
            p.rating,
            p.tag,
            p.description,
            p.in_stock,
        ] for p in products
    ]


@router.get("/contact")
def get_all_contacts(db: Session = Depends(get_db), owner=Depends(require_owner)):
    contacts = db.query(Contact).all()
    return [
        [
            c.id,
            c.name,
            c.email,
            c.phone,
            c.subject,
            c.message,
        ]
        for c in contacts
    ]


def appointment_row(a) -> list:
    return [
        a.id,
        a.name,
        a.email,
        a.phone,
        a.message,
        a.appointment_date,
        a.status or "pending",
        a.original_date,
        a.owner_note,
    ]


@router.get("/appointments")
def get_all_appointments(db: Session = Depends(get_db), owner=Depends(require_owner)):
    appointments = db.query(Contact).filter(Contact.subject == "Showroom Visit").order_by(Contact.id.desc()).all()
    return [appointment_row(a) for a in appointments]


class AppointmentDecision(BaseModel):
    action: Literal["accept", "decline", "adjust"]
    new_date: Optional[str] = Field(default=None, description="YYYY-MM-DD, required for 'adjust'")
    note: Optional[str] = Field(default=None, max_length=300)


def _pretty(d: Optional[str]) -> str:
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%d %b %Y")
    except (TypeError, ValueError):
        return d or "the requested date"


@router.patch("/appointments/{appointment_id}")
def decide_appointment(appointment_id: int, data: AppointmentDecision, db: Session = Depends(get_db), owner=Depends(require_owner)):
    appt = db.query(Contact).filter(Contact.id == appointment_id, Contact.subject == "Showroom Visit").first()
    if not appt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    note = (data.note or "").strip() or None
    current = appt.appointment_date

    if data.action == "adjust":
        try:
            new_day = datetime.strptime((data.new_date or "").strip(), "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=422, detail="Please choose a valid new date.")
        if new_day < date.today():
            raise HTTPException(status_code=422, detail="The new date cannot be in the past.")
        if new_day.isoformat() == (current or ""):
            raise HTTPException(status_code=422, detail="That is already the appointment date. Pick a different one.")
        if not appt.original_date:
            appt.original_date = current
        appt.appointment_date = new_day.isoformat()
        appt.status = "rescheduled"
    elif data.action == "accept":
        appt.status = "accepted"
    else:
        appt.status = "declined"

    appt.owner_note = note
    appt.decided_at = datetime.utcnow()
    db.commit()
    db.refresh(appt)

    extra = f" Note from the store: {note}" if note else ""
    if data.action == "accept":
        notify(db, appt.user_id, "appointment_accepted", "Appointment confirmed",
               f"Your showroom visit on {_pretty(appt.appointment_date)} has been accepted. We look forward to seeing you!{extra}", "/contact")
    elif data.action == "decline":
        notify(db, appt.user_id, "appointment_declined", "Appointment declined",
               f"Sorry, we can't host your showroom visit on {_pretty(current)}. You are welcome to request another date.{extra}", "/contact")
    else:
        notify(db, appt.user_id, "appointment_rescheduled", "Appointment date changed",
               f"Your showroom visit was moved from {_pretty(current)} to {_pretty(appt.appointment_date)}.{extra}", "/contact")

    return appointment_row(appt)


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
    return [
    new_product.id,
    new_product.name,
    new_product.image,
    new_product.category,
    new_product.price,
    new_product.oldPrice,
    new_product.rating,
    new_product.tag,
    new_product.description,
    new_product.in_stock,
    ]



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
    return [
    product.id,
    product.name,
    product.image,
    product.category,
    product.price,
    product.oldPrice,
    product.rating,
    product.tag,
    product.description,
    product.in_stock,
    ]


@router.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), owner=Depends(require_owner)):
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.query(Images).filter(Images.product_id == product.id).delete()
    db.query(Cart).filter(Cart.product_id == product.id).delete()
    db.query(Wishlist).filter(Wishlist.product_id == product.id).delete()
    db.delete(product)
    db.commit()
    return {"message": "Product deleted Successfully"}


@router.get("/orders")
def get_all_orders(db: Session = Depends(get_db), owner=Depends(require_owner)):
    orders = db.query(Order).all()
    return [
        [
            o.id,
            o.user_name,
            o.userEmail,
            o.name,
            o.category,
            o.price,
            o.quantity,
            o.total_price,
            o.in_stock,
            o.status,
        ] for o in orders
    ]


@router.patch("/orders/{order_id}")
def update_order_status(order_id: int, data: OrderStatusUpdate, db: Session = Depends(get_db), owner=Depends(require_owner)):
    order = db.query(Order).filter(Order.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    previous = order.status
    order.status = data.status

    db.commit()
    db.refresh(order)
    if data.status != previous:
        notify(db, order.user_id, "order_updated", "Order update",
               f"Your order #{order.id} ({order.name}) is now {data.status}.", "/cart")
    return [
    order.id,
    order.user_name,
    order.userEmail,
    order.name,
    order.category,
    order.price,
    order.quantity,
    order.total_price,
    order.in_stock,
    order.status,
    ]



def appointment_dict(c) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "email": c.email,
        "phone": c.phone,
        "appointment_date": c.appointment_date,
        "message": c.message,
    }

