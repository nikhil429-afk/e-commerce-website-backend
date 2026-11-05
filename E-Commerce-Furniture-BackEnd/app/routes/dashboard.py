from typing import List
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schema.product import Product, Images
from app.models.product import ProductResponse
from app.routes.product import _products_payload, LIST_CACHE

router = APIRouter(prefix="", tags=["Dashboard"])


@router.get("/products")
def get_products(response: Response, db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = LIST_CACHE
    return _products_payload(db)
