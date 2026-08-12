from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from app.core.security import get_current_user, require_owner
from app.schema.wishlist import Wishlist
from app.schema.product import Product, Images
from app.core.database import get_db
from sqlalchemy.orm import Session
from typing import Optional, List
from app.schema.cart import Cart
import shutil, os, uuid


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "assets", "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter(prefix="/products", tags=["Products"])


def _product_dict(p, db) -> dict:
    extra_images = db.query(Images).filter(Images.product_id == p.id).all()
    all_images = [p.image]

    for img in extra_images:
        all_images.append(img.file_path)

    return {
        "id": p.id,
        "name": p.name or "",
        "images": all_images,
        "category": p.category or "",
        "price": p.price or 0,
        "oldPrice": p.oldPrice or 0,
        "rating": p.rating or 0,
        "tag": p.tag or "",
        "description": p.description or "",
        "in_stock": p.in_stock if p.in_stock is not None else True,
    }


@router.get("/")
def get_products(db: Session = Depends(get_db)):

    products = db.query(Product).all()
    final_products = []

    for product in products:
        extra_images = db.query(Images).filter(Images.product_id == product.id).all()

        all_images = [product.image]

        for img in extra_images:
            all_images.append(img.file_path)

        final_products.append({
            "id": product.id,
            "name": product.name,
            "category": product.category,
            "images": all_images,
            "price": product.price,
            "oldPrice": product.oldPrice,
            "description": product.description,
            "rating": product.rating,
            "tag": product.tag,
            "in_stock": product.in_stock,
        })

    return final_products


@router.post("/")
async def create_product(
    name: str = Form(...),
    category: str = Form(...),
    images: List[UploadFile] = File(...),
    price: float = Form(...),
    oldPrice: float = Form(...),
    rating: int = Form(...),
    tag: str = Form(...),
    description: str = Form(...),
    in_stock: bool = Form(...),
    db: Session = Depends(get_db),
    owner=Depends(require_owner),
    ):

    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        uploaded_paths = []

        for image in images:

            file_ext = image.filename.split(".")[-1]

            unique_filename = f"{uuid.uuid4()}.{file_ext}"

            file_path = os.path.join(UPLOAD_DIR, unique_filename)

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)

            image_url = f"/uploads/{unique_filename}"

            uploaded_paths.append(image_url)

        product = Product(
            name=name,
            image=uploaded_paths[0],
            category=category,
            price=price,
            oldPrice=oldPrice,
            rating=rating,
            tag=tag,
            description=description,
            in_stock=in_stock,
        )

        db.add(product)

        db.commit()

        db.refresh(product)

        for extra_image in uploaded_paths[1:]:
            new_image = Images(product_id=product.id, file_path=extra_image)

            db.add(new_image)

        db.commit()

        return {"message": "Product created Successfully", "product": _product_dict(product, db)}

    except Exception as e:

        import traceback
        # traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{product_id}")
async def update_product(
    product_id: int,
    images: Optional[List[UploadFile]] = File(None),
    name: str = Form(...),
    category: str = Form(...),
    price: float = Form(...),
    oldPrice: float = Form(...),
    rating: int = Form(...),
    tag: str = Form(...),
    description: str = Form(...),
    in_stock: bool = Form(...),
    db: Session = Depends(get_db),
    owner=Depends(require_owner),
    ):

    existing = db.query(Product).filter(Product.id == product_id).first()

    if not existing:
        raise HTTPException(status_code=404, detail="Product Not Found!")

    if images:

        uploaded_paths = []

        for image in images:

            file_ext = image.filename.split(".")[-1]
            unique_filename = f"{uuid.uuid4()}.{file_ext}"

            file_path = os.path.join(
                UPLOAD_DIR,
                unique_filename
            )

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)

            image_url = f"/uploads/{unique_filename}"

            uploaded_paths.append(image_url)

        existing.image = uploaded_paths[0]

        db.query(Images).filter(Images.product_id == existing.id).delete()

        for extra_image in uploaded_paths[1:]:

            new_image = Images(product_id=existing.id,file_path=extra_image)
            db.add(new_image)

    existing.name = name
    existing.category = category
    existing.price = price
    existing.oldPrice = oldPrice
    existing.rating = rating
    existing.tag = tag
    existing.description = description
    existing.in_stock = in_stock

    db.commit()
    db.refresh(existing)

    return {"message": "Product updated successfully", "product": _product_dict(existing, db)}


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), owner=Depends(require_owner)):
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product Not Found!")
    
    db.delete(product)
    db.commit()
    return {"message": "Product Deleted Successfully"}


@router.get("/cart")
def get_cart(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(Cart).all()


@router.get("/wishlist")
def get_wishlist(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return db.query(Wishlist).all()


@router.post("/wishlist/{product_id}/add")
def add_to_wishlist(product_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product Not Found!")
    
    user.wishlist.append(product)
    db.commit()
    return {"message": "Product Added to Wishlist"}


@router.delete("/wishlist/{product_id}/remove")
def remove_from_wishlist(product_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product Not Found!")
    
    user.wishlist.remove(product)
    db.commit()
    return {"message": "Product Removed from Wishlist"}


@router.put("/cart/{product_id}/add")
def add_to_cart(product_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product Not Found!")
    
    user.cart.append(product)
    db.commit()
    return {"message": "Product Added to Cart"}


@router.delete("/cart/{product_id}/remove")
def remove_from_cart(product_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product Not Found!")
    
    user.cart.remove(product)
    db.commit()
    return {"message": "Product Removed from Cart"}


@router.get("/almirahs")
def get_almirahs(db: Session = Depends(get_db)):
    return [_product_dict(p, db) for p in db.query(Product).filter(Product.category == "almirahs").all()]

@router.get("/beds")
def get_beds(db: Session = Depends(get_db)):
    return [_product_dict(p, db) for p in db.query(Product).filter(Product.category == "beds").all()]

@router.get("/chairs")
def get_chairs(db: Session = Depends(get_db)):
    return [_product_dict(p, db) for p in db.query(Product).filter(Product.category == "chairs").all()]

@router.get("/dinings")
def get_dinings(db: Session = Depends(get_db)):
    return [_product_dict(p, db) for p in db.query(Product).filter(Product.category == "dinings").all()]

@router.get("/sofas")
def get_sofas(db: Session = Depends(get_db)):
    return [_product_dict(p, db) for p in db.query(Product).filter(Product.category == "sofas").all()]

@router.get("/tables")
def get_tables(db: Session = Depends(get_db)):
    return [_product_dict(p, db) for p in db.query(Product).filter(Product.category == "tables").all()]
