from unittest import result

from fastapi import APIRouter, Depends
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.security import require_owner
from app.core.database import get_db
from app.schema.order import Order
from app.schema.register import User

class DateRange(BaseModel):
    start_day: datetime
    end_day: datetime

router = APIRouter(prefix="/owner", tags=["Charts"])


@router.get("/orders/chart")
def orders_chart(start: str, end: str, db: Session = Depends(get_db), owner=Depends(require_owner)):
    start_date = datetime.fromisoformat(start.replace("Z", ""))
    end_date = datetime.fromisoformat(end.replace("Z", "")) + timedelta(days=1)

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    end_date += timedelta(days=1)

    orders = (db.query(Order).filter(Order.created_at >= start_date).filter(Order.created_at < end_date).all())

    daily_orders = {}

    for order in orders:
        day = order.created_at.date()
        daily_orders[day] = daily_orders.get(day, 0) + 1

    return [{"label": day.strftime("%d %b"), "value": count} for day, count in sorted(daily_orders.items())]


@router.get("/users/chart")
def users_chart(start: str, end: str, db: Session = Depends(get_db), owner=Depends(require_owner)):
    start_date = datetime.fromisoformat(start.replace("Z", ""))
    end_date = datetime.fromisoformat(end.replace("Z", "")) + timedelta(days=1)

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    end_date += timedelta(days=1)
    
    users = (db.query(User).filter(User.created_at >= start_date).filter(User.created_at < end_date).all())
    
    daily_users = {}

    for user in users:
        day = user.created_at.date()
        daily_users[day] = daily_users.get(day, 0) + 1

    return [{"label": day.strftime("%d %b"), "value": count} for day, count in sorted(daily_users.items())]
    

# @router.get("/visitors/chart")
# def get_leads_per_day(start: str, end: str, owner: dict = Depends(require_owner), db: Session = Depends(get_db)):
#     start_date = datetime.fromisoformat(start)
#     end_date = datetime.fromisoformat(end)

#     visitors = db.query(User).all()

#     chart = []
#     total = 0

#     for v in visitors:
#         total += 1
#         chart.append({"label": v.strftime("%d %b"), "value": total, "total": total})

#     return total