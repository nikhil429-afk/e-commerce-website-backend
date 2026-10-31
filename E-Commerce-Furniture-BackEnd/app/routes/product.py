from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from app.core.security import require_owner
from app.core.config import MAX_IMAGE_BYTES
from app.schema.product import Product, Images
from app.schema.wishlist import Wishlist
from app.schema.cart import Cart
from app.core.database import get_db
from sqlalchemy.orm import Session
from typing import Optional, List
import logging, os, uuid

log = logging.getLogger("products")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "assets", "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "avif", "gif"}

router = APIRouter(prefix="/products", tags=["Products"])


# GET /products (no slash) is served by routes/dashboard.py; the home page calls GET /products/ (with slash).
@router.get("/")
def get_all_products(db: Session = Depends(get_db)):
    return [_product_dict(p, db) for p in db.query(Product).all()]


def _product_dict(p, db) -> dict:
    extra_images = db.query(Images).filter(Images.product_id == p.id).all()
    all_images = [p.image] if p.image else []

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


async def _save_images(images: List[UploadFile]) -> List[str]:
    """Validate every image first, then write them. Returns the public /uploads/... urls."""
    prepared = []

    for image in images:
        if not image.filename:
            continue

        ext = image.filename.rsplit(".", 1)[-1].lower() if "." in image.filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"'{image.filename}' is not a supported image (use JPG, PNG, WEBP, AVIF or GIF).")

        if image.content_type and not image.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail=f"'{image.filename}' is not an image file.")

        data = await image.read()
        if not data:
            raise HTTPException(status_code=400, detail=f"'{image.filename}' is empty.")
        if len(data) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail=f"'{image.filename}' is larger than {MAX_IMAGE_BYTES // (1024 * 1024)} MB.")

        prepared.append((ext, data))

    saved_urls, saved_paths = [], []
    try:
        for ext, data in prepared:
            name = f"{uuid.uuid4()}.{ext}"
            path = os.path.join(UPLOAD_DIR, name)
            with open(path, "wb") as buffer:
                buffer.write(data)
            saved_paths.append(path)
            saved_urls.append(f"/uploads/{name}")
    except OSError:
        _remove_files(saved_urls)
        log.exception("Could not write uploaded images")
        raise HTTPException(status_code=500, detail="Could not store the uploaded images.")

    return saved_urls


def _remove_files(urls: List[str]) -> None:
    for url in urls:
        if not url or not url.startswith("/uploads/"):
            continue
        path = os.path.join(UPLOAD_DIR, os.path.basename(url))
        try:
            os.remove(path)
        except OSError:
            pass


@router.post("/")
async def create_product(
    name: str = Form(..., min_length=1, max_length=191),
    category: str = Form(..., min_length=1, max_length=100),
    images: List[UploadFile] = File(...),
    price: float = Form(..., ge=0),
    oldPrice: float = Form(0, ge=0),
    rating: int = Form(0, ge=0, le=5),
    tag: str = Form("", max_length=100),
    description: str = Form(""),
    in_stock: bool = Form(True),
    db: Session = Depends(get_db),
    owner=Depends(require_owner),
):
    urls = await _save_images(images)
    if not urls:
        raise HTTPException(status_code=400, detail="Please add at least one product image.")

    try:
        product = Product(
            name=name.strip(),
            image=urls[0],
            category=category.strip().lower(),
            price=price,
            oldPrice=oldPrice,
            rating=rating,
            tag=tag.strip(),
            description=description.strip(),
            in_stock=in_stock,
        )
        db.add(product)
        db.flush()                                   # get product.id without committing yet

        for extra in urls[1:]:
            db.add(Images(product_id=product.id, file_path=extra))

        db.commit()                                  # product + images are saved together or not at all
        db.refresh(product)
    except Exception:
        db.rollback()
        _remove_files(urls)
        log.exception("Creating product failed")
        raise HTTPException(status_code=500, detail="Could not save the product. Nothing was changed.")

    return {"message": "Product created Successfully", "product": _product_dict(product, db)}


@router.put("/{product_id}")
async def update_product(
    product_id: int,
    images: Optional[List[UploadFile]] = File(None),
    name: str = Form(..., min_length=1, max_length=191),
    category: str = Form(..., min_length=1, max_length=100),
    price: float = Form(..., ge=0),
    oldPrice: float = Form(0, ge=0),
    rating: int = Form(0, ge=0, le=5),
    tag: str = Form("", max_length=100),
    description: str = Form(""),
    in_stock: bool = Form(True),
    db: Session = Depends(get_db),
    owner=Depends(require_owner),
):
    existing = db.query(Product).filter(Product.id == product_id).first()

    if not existing:
        raise HTTPException(status_code=404, detail="Product Not Found!")

    new_urls: List[str] = []
    old_urls: List[str] = []

    if images and any(i.filename for i in images):
        new_urls = await _save_images(images)

    try:
        if new_urls:
            old_urls = [existing.image] + [i.file_path for i in db.query(Images).filter(Images.product_id == existing.id).all()]
            existing.image = new_urls[0]
            db.query(Images).filter(Images.product_id == existing.id).delete()
            for extra in new_urls[1:]:
                db.add(Images(product_id=existing.id, file_path=extra))

        existing.name = name.strip()
        existing.category = category.strip().lower()
        existing.price = price
        existing.oldPrice = oldPrice
        existing.rating = rating
        existing.tag = tag.strip()
        existing.description = description.strip()
        existing.in_stock = in_stock

        db.commit()
        db.refresh(existing)
    except Exception:
        db.rollback()
        _remove_files(new_urls)
        log.exception("Updating product %s failed", product_id)
        raise HTTPException(status_code=500, detail="Could not update the product. Nothing was changed.")

    _remove_files(old_urls)                          # old pictures are deleted only after the DB commit worked
    return {"message": "Product updated successfully", "product": _product_dict(existing, db)}


@router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db), owner=Depends(require_owner)):
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        raise HTTPException(status_code=404, detail="Product Not Found!")

    db.query(Images).filter(Images.product_id == product.id).delete()
    db.query(Cart).filter(Cart.product_id == product.id).delete()
    db.query(Wishlist).filter(Wishlist.product_id == product.id).delete()
    db.delete(product)
    db.commit()
    return {"message": "Product Deleted Successfully"}


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
