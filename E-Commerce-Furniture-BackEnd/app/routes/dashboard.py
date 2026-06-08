from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schema.product import Product, Images
from app.models.product import ProductResponse

router = APIRouter(prefix="", tags=["Dashboard"])


@router.get("/products")
def get_products(db: Session = Depends(get_db)):

    products = db.query(Product).all()
    result = []

    for product in products:
        extra_images = db.query(Images).filter(Images.product_id == product.id).all()

        image_list = [product.image]

        for img in extra_images:
            image_list.append(img.file_path)

        result.append({
            "id": product.id,
            "name": product.name,
            "category": product.category,
            "price": product.price,
            "oldPrice": product.oldPrice,
            "tag": product.tag,
            "rating": product.rating,
            "description": product.description,
            "in_stock": product.in_stock,
            "images": image_list
        })

    return result

