"""Small, cached WebP copies of the uploaded product photos.

The owner uploads full-size photos (often several MB). Sending those to every product card is what makes the
products page crawl, so the site asks for  /thumb/<file>?w=480  instead. The first request makes the small
copy, every later request is served straight from disk with a one-year browser cache.
"""
import logging
import os

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from PIL import Image, ImageOps

log = logging.getLogger("media")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "assets", "uploads")
THUMB_DIR = os.path.join(BASE_DIR, "assets", "thumbs")
os.makedirs(THUMB_DIR, exist_ok=True)

ALLOWED_WIDTHS = (240, 360, 480, 720, 1080, 1440)
IMMUTABLE = {"Cache-Control": "public, max-age=31536000, immutable"}

router = APIRouter(tags=["Media"])


def _snap(width: int) -> int:
    """Only a few fixed sizes are ever generated, so the disk cannot be filled with arbitrary sizes."""
    for w in ALLOWED_WIDTHS:
        if width <= w:
            return w
    return ALLOWED_WIDTHS[-1]


@router.get("/thumb/{name}")
def thumbnail(name: str, w: int = Query(480, ge=1, le=4000)):
    name = os.path.basename(name)
    source = os.path.join(UPLOAD_DIR, name)
    if not os.path.isfile(source):
        raise HTTPException(status_code=404, detail="Image not found")

    width = _snap(w)
    target = os.path.join(THUMB_DIR, f"{width}_{os.path.splitext(name)[0]}.webp")

    if not os.path.isfile(target):
        try:
            with Image.open(source) as im:
                im = ImageOps.exif_transpose(im)
                if im.width > width:
                    im = im.resize((width, max(1, round(im.height * width / im.width))), Image.LANCZOS)
                if im.mode not in ("RGB", "RGBA"):
                    im = im.convert("RGBA" if "transparency" in im.info else "RGB")
                tmp = target + ".part"
                im.save(tmp, "WEBP", quality=78, method=4)
                os.replace(tmp, target)
        except Exception:
            log.exception("Could not make a thumbnail for %s", name)
            return FileResponse(source, headers=IMMUTABLE)       # fall back to the original

    return FileResponse(target, media_type="image/webp", headers=IMMUTABLE)
