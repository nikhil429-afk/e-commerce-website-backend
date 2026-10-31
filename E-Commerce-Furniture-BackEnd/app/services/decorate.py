
"""AI room decorator.

Two steps, so the recommendations are realistic instead of a single guess:

  1. VISION  - Gemini looks at the photo and describes the room (type, style, colours, what furniture is
               already there) and finds the genuinely free spaces (position, size, where it sits).
  2. MATCH   - the SERVER builds a shortlist per space from the real catalogue using furniture-sense rules
               (no bed in a small corner, no second sofa in a living room that has one, nothing that
               doesn't belong in that kind of room), scores it against the room's style and palette, and
               only then asks Gemini to pick and rank from that shortlist and explain why.

Whatever Gemini says is checked against the database: only real in-stock product ids survive, and names,
prices and images always come from the database. If step 2 fails the server falls back to its own ranking,
so the user still gets sensible results.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from google import genai
from google.genai import types
from PIL import Image, ImageOps, UnidentifiedImageError
import io, os, json, re, logging

from app.schema.product import Product, Images
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import GEMINI_MODEL, GEMINI_FALLBACK_MODELS, MAX_ROOM_IMAGE_BYTES

log = logging.getLogger("ai-decorate")

router = APIRouter(prefix="/ai-decorate", tags=["AI-Vision"])

ALLOWED_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAX_SIDE = 1600
MAX_SPACES = 4
MAX_PER_SPACE = 5
MIN_PER_SPACE = 3
SHORTLIST_SIZE = 12
SHORTLIST_PER_CATEGORY = 5

ROOM_TYPES = ["living_room", "bedroom", "dining_room", "kitchen", "office", "hallway", "other"]
STYLES = ["modern", "minimalist", "contemporary", "traditional", "rustic", "industrial", "scandinavian", "bohemian", "classic", "other"]
POSITIONS = ["corner", "wall", "center", "window", "entrance", "other"]
SIZES = ["small", "medium", "large"]

# What does not belong in which kind of room / space (exclusion lists, so unknown categories stay allowed).
ROOM_EXCLUDE = {
    "living_room": {"beds", "dinings"},
    "bedroom": {"sofas", "dinings"},
    "dining_room": {"beds", "sofas"},
    "kitchen": {"beds", "sofas", "almirahs"},
    "office": {"beds", "sofas", "dinings"},
    "hallway": {"beds", "sofas", "dinings"},
    "other": set(),
}
SIZE_EXCLUDE = {"small": {"beds", "dinings", "almirahs", "sofas"}, "medium": {"beds"}, "large": set()}
BIG_ITEMS = {"beds", "sofas", "dinings", "almirahs"}      # a room rarely needs a second one

_working_model = {"name": None}


def gemini_client():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="The AI decorator is not configured (GOOGLE_API_KEY missing).")
    return genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=60_000))


# ------------------------------------------------------------------ helpers
def _models():
    names = [_working_model["name"]] if _working_model["name"] else []
    for n in [GEMINI_MODEL, *GEMINI_FALLBACK_MODELS]:
        if n and n not in names:
            names.append(n)
    return names


def _generate_json(client, contents, temperature=0.3):
    """Call Gemini, trying the configured model first and then the fallbacks if a model is unavailable."""
    last = None
    for model in _models():
        try:
            response = client.models.generate_content(
                model=model, contents=contents,
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=temperature),
            )
            _working_model["name"] = model
            return _parse_json(response.text)
        except (ValueError, TypeError, AttributeError) as e:      # unreadable output: one retry on the same model
            last = e
            try:
                response = client.models.generate_content(
                    model=model, contents=contents,
                    config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.1),
                )
                _working_model["name"] = model
                return _parse_json(response.text)
            except Exception as e2:
                last = e2
                break
        except Exception as e:
            last = e
            msg = str(e).lower()
            if any(k in msg for k in ("404", "not_found", "not found", "is not supported", "no longer available")):
                log.warning("Gemini model %s unavailable, trying the next one", model)
                continue
            raise
    raise last if last else RuntimeError("no model available")


def _parse_json(text: str):
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("not an object")
    return data


def _clamp(value, low, high, default):
    try:
        return max(low, min(high, int(round(float(value)))))
    except (TypeError, ValueError):
        return default


def _enum(value, allowed, default):
    v = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    return v if v in allowed else default


def _label(room_type: str) -> str:
    return room_type.replace("_", " ")


# ------------------------------------------------------------------ step 1: vision
def _vision_prompt(categories: list) -> str:
    return f"""You are a senior interior designer analysing a customer's room photo for a furniture store.

Our store sells ONLY these furniture categories: {json.dumps(categories)}.

1. Describe the room: its type, style and 2-4 dominant colours/materials.
2. List which of OUR categories are ALREADY clearly present in the photo (existing_furniture).
3. Find up to {MAX_SPACES} genuinely EMPTY spots where one of our pieces could realistically stand
   (free floor or free wall - never on top of existing furniture, never blocking a door or the main walkway).
   For each spot say where it is, how big the free area is, which of OUR categories physically suit it, and
   one practical placement tip.

If the image is not an interior room, or there is no usable free space, return an empty empty_spaces list.

Return ONLY this JSON (no markdown):
{{"room": {{"type": one of {ROOM_TYPES}, "style": one of {STYLES},
           "palette": ["colour or material", "..."], "summary": "one sentence about the room"}},
 "existing_furniture": ["category", "..."],
 "empty_spaces": [{{"label": "short name e.g. Corner beside the window",
                    "box_2d": [ymin, xmin, ymax, xmax],
                    "position": one of {POSITIONS}, "size": one of {SIZES},
                    "suitable_categories": ["category", "..."],
                    "note": "one short practical tip"}}]}}

box_2d values are integers 0-1000 relative to the image and must tightly outline the FREE area."""


def _clean_vision(raw: dict, categories: list) -> dict:
    cats = set(categories)
    room_raw = raw.get("room") if isinstance(raw.get("room"), dict) else {}
    room = {
        "type": _enum(room_raw.get("type"), ROOM_TYPES, "other"),
        "style": _enum(room_raw.get("style"), STYLES, "other"),
        "palette": [str(p).strip()[:30] for p in (room_raw.get("palette") or []) if str(p).strip()][:4],
        "summary": str(room_raw.get("summary") or "").strip()[:220],
    }
    existing = {str(c).strip().lower() for c in (raw.get("existing_furniture") or [])} & cats

    spaces = []
    for s in (raw.get("empty_spaces") or [])[:MAX_SPACES]:
        if not isinstance(s, dict):
            continue
        box = s.get("box_2d")
        if isinstance(box, list) and len(box) == 4:
            y1, x1, y2, x2 = [_clamp(v, 0, 1000, 0) for v in box]
            if y2 < y1: y1, y2 = y2, y1
            if x2 < x1: x1, x2 = x2, x1
        else:
            y1 = x1 = y2 = x2 = 0
        spaces.append({
            "label": str(s.get("label") or "Empty space").strip()[:80],
            "box_2d": [y1, x1, y2, x2],
            "position": _enum(s.get("position"), POSITIONS, "other"),
            "size": _enum(s.get("size"), SIZES, "medium"),
            "suitable": {str(c).strip().lower() for c in (s.get("suitable_categories") or [])} & cats,
            "note": str(s.get("note") or "").strip()[:200],
        })
    return {"room": room, "existing": existing, "spaces": spaces}


# ------------------------------------------------------------------ step 2: realistic shortlist
def _allowed_categories(space: dict, room: dict, existing: set, catalog_cats: set) -> set:
    def apply(use_existing=True, use_size=True, use_suggested=True):
        allowed = set(catalog_cats)
        if use_suggested and space["suitable"]:
            allowed &= space["suitable"]
        allowed -= ROOM_EXCLUDE.get(room["type"], set())
        if use_size:
            exclude = set(SIZE_EXCLUDE[space["size"]])
            if space["size"] == "medium" and room["type"] == "bedroom" and "beds" not in existing:
                exclude.discard("beds")
            allowed -= exclude
        if use_existing and space["size"] != "large":
            allowed -= (existing & BIG_ITEMS)
        return allowed

    for flags in ({}, {"use_existing": False}, {"use_existing": False, "use_size": False},
                  {"use_existing": False, "use_size": False, "use_suggested": False}):
        allowed = apply(**flags)
        if allowed:
            return allowed
    return set(catalog_cats)


def _style_terms(room: dict) -> set:
    words = set()
    for chunk in [room["style"], room["type"].replace("_", " "), *room["palette"]]:
        for w in re.findall(r"[a-z]{3,}", chunk.lower()):
            if w not in {"other", "the", "and", "with"}:
                words.add(w)
    return words


def _score(product: dict, terms: set) -> float:
    text = f"{product['name']} {product['description']} {product['tag']} {product['category']}".lower()
    hits = sum(1 for t in terms if t in text)
    bonus = 0.4 if product["tag"].lower() in {"popular", "trending", "bestseller", "new"} else 0
    return hits * 2 + product["rating"] * 0.5 + bonus


def _shortlist(allowed: set, products: list, terms: set, used: set) -> list:
    pool = [p for p in products if p["category"] in allowed]
    pool.sort(key=lambda p: _score(p, terms), reverse=True)
    per_cat, out = {}, []
    for p in pool:
        if per_cat.get(p["category"], 0) >= SHORTLIST_PER_CATEGORY:
            continue
        per_cat[p["category"]] = per_cat.get(p["category"], 0) + 1
        out.append(p)
        if len(out) >= SHORTLIST_SIZE:
            break
    # products already used by an earlier space go to the back so each piece is suggested once
    return [p for p in out if p["id"] not in used] + [p for p in out if p["id"] in used]


def _match_prompt(room: dict, existing: set, jobs: list) -> str:
    blocks = []
    for j in jobs:
        sp = j["space"]
        blocks.append({
            "index": j["index"], "space": sp["label"], "position": sp["position"], "free_area": sp["size"],
            "tip": sp["note"],
            "shortlist": [{"product_id": p["id"], "name": p["name"], "category": p["category"], "price": p["price"],
                           "tag": p["tag"], "description": p["description"][:140]} for p in j["shortlist"]],
        })
    return f"""You are a senior interior stylist for a furniture store.

ROOM: {json.dumps({"type": _label(room["type"]), "style": room["style"], "palette": room["palette"],
                    "already_has": sorted(existing), "summary": room["summary"]})}

For EACH space below choose {MIN_PER_SPACE}-{MAX_PER_SPACE} products from THAT space's shortlist, best match first.
Judge: physical fit for the free area and position, harmony with the room's style and palette, not duplicating
what the room already has, variety (never several near-identical pieces) and a sensible price spread.
product_id MUST come from that space's shortlist. Never invent products. Use each product once overall.

SPACES: {json.dumps(blocks, ensure_ascii=False)}

Return ONLY this JSON:
{{"spaces": [{{"index": 0, "picks": [{{"product_id": 1, "confidence": 90,
   "reason": "one concrete sentence that refers to THIS room (max 24 words)",
   "tags": ["Fits the corner", "Warm tone"]}}]}}]}}

confidence: integer 60-98, honest and descending. tags: 2-3 chips of at most 3 words."""


def _fallback_picks(shortlist: list, space: dict, room: dict, used: set, terms: set) -> list:
    picks = []
    for p in shortlist:
        if p["id"] in used:
            continue
        s = _score(p, terms)
        picks.append({
            "product_id": p["id"], "confidence": _clamp(62 + s * 3, 60, 88, 70),
            "reason": f"A {p['category'].rstrip('s')} like this suits the {space['position']} of your {_label(room['type'])}.",
            "tags": [f"Fits the {space['position']}" if space["position"] != "other" else "Good fit", (room["style"].title() if room["style"] != "other" else "Versatile")],
        })
        if len(picks) >= 4:
            break
    return picks


def _build_output(vision: dict, jobs: list, ai: dict | None, by_id: dict, terms: set) -> list:
    ai_spaces = {}
    if ai and isinstance(ai.get("spaces"), list):
        for item in ai["spaces"]:
            if isinstance(item, dict):
                ai_spaces[_clamp(item.get("index"), 0, 99, -1)] = item.get("picks") or []

    used, out = set(), []
    for j in jobs:
        allowed_ids = {p["id"] for p in j["shortlist"]}
        picks = []
        for rec in ai_spaces.get(j["index"], []):
            if not isinstance(rec, dict):
                continue
            pid = _clamp(rec.get("product_id"), 0, 10**9, None)
            if pid not in allowed_ids or pid in used or any(p["product_id"] == pid for p in picks):
                continue
            picks.append({
                "product_id": pid, "confidence": _clamp(rec.get("confidence"), 55, 99, 75),
                "reason": str(rec.get("reason") or "").strip()[:240],
                "tags": [str(t).strip()[:24] for t in (rec.get("tags") or []) if str(t).strip()][:3],
            })
            if len(picks) >= MAX_PER_SPACE:
                break

        if len(picks) < 2:        # the AI returned too little for this space: top up with our own ranking
            have = {p["product_id"] for p in picks}
            for extra in _fallback_picks(j["shortlist"], j["space"], vision["room"], used | have, terms):
                picks.append(extra)
                if len(picks) >= MIN_PER_SPACE:
                    break

        picks.sort(key=lambda p: p["confidence"], reverse=True)
        if not picks:
            continue

        products = []
        for rank, rec in enumerate(picks, start=1):
            used.add(rec["product_id"])
            p = by_id[rec["product_id"]]
            products.append({
                "rank": rank, "product_id": p["id"], "name": p["name"], "category": p["category"],
                "image": p["image"], "images": p["images"], "price": p["price"], "oldPrice": p["oldPrice"],
                "rating": p["rating"], "tag": p["tag"], "confidence": rec["confidence"],
                "reason": rec["reason"] or f"A good match for the {j['space']['label'].lower()}.",
                "tags": rec["tags"],
            })
        sp = j["space"]
        out.append({
            "space_description": sp["label"], "box_2d": sp["box_2d"], "position": sp["position"],
            "size": sp["size"], "note": sp["note"], "recommended_products": products,
        })
    return out


# ------------------------------------------------------------------ endpoint
@router.post("")
async def upload_room(file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only JPG, PNG and WEBP images are allowed.")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(image_bytes) > MAX_ROOM_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail=f"Image is too large (max {MAX_ROOM_IMAGE_BYTES // (1024 * 1024)} MB).")

    try:
        room_image = ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes)))
        room_image = room_image.convert("RGB")
        room_image.thumbnail((MAX_SIDE, MAX_SIDE))
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="That file could not be read as an image.")

    rows = db.query(Product).filter(Product.in_stock == True).all()  # noqa: E712
    if not rows:
        return JSONResponse(status_code=200, content={"success": True, "filename": file.filename, "room": None,
                                                      "empty_spaces": [], "message": "There are no products in stock to recommend yet."})

    extra = {}
    for img in db.query(Images).filter(Images.product_id.in_([p.id for p in rows])).all():
        extra.setdefault(img.product_id, []).append(img.file_path)

    products, by_id = [], {}
    for p in rows:
        item = {
            "id": p.id, "name": p.name or "", "category": (p.category or "").strip().lower(), "image": p.image or "",
            "images": ([p.image] if p.image else []) + extra.get(p.id, []), "price": p.price or 0,
            "oldPrice": p.oldPrice or 0, "rating": p.rating or 0, "tag": p.tag or "", "description": p.description or "",
        }
        products.append(item); by_id[p.id] = item
    categories = sorted({p["category"] for p in products if p["category"]})

    client = gemini_client()

    # ---- step 1: understand the room
    try:
        raw = await run_in_threadpool(_generate_json, client, [room_image, _vision_prompt(categories)])
    except HTTPException:
        raise
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(status_code=502, detail="The AI returned an unreadable answer. Please try again.")
    except Exception:
        log.exception("Gemini room analysis failed")
        raise HTTPException(status_code=502, detail="The AI service could not analyse the room right now. Please try again.")

    vision = _clean_vision(raw, categories)
    room, existing = vision["room"], vision["existing"]
    terms = _style_terms(room)

    # ---- step 2: realistic shortlist per space
    catalog_cats = set(categories)
    jobs, used_for_order = [], set()
    for idx, space in enumerate(vision["spaces"]):
        allowed = _allowed_categories(space, room, existing, catalog_cats)
        shortlist = _shortlist(allowed, products, terms, used_for_order)
        if shortlist:
            jobs.append({"index": idx, "space": space, "shortlist": shortlist})
            used_for_order.update(p["id"] for p in shortlist[:MIN_PER_SPACE])

    if not jobs:
        return JSONResponse(status_code=200, content={
            "success": True, "filename": file.filename, "room": _room_out(room, existing), "empty_spaces": [],
            "message": "We could not find a free spot for our furniture in this photo. Try a wider shot of the room.",
        })

    ai = None
    try:
        ai = await run_in_threadpool(_generate_json, client, [_match_prompt(room, existing, jobs)], 0.4)
    except Exception:
        log.warning("Gemini matching step failed - using the server ranking instead", exc_info=True)

    spaces = _build_output(vision, jobs, ai, by_id, terms)

    return JSONResponse(status_code=200, content={
        "success": True, "filename": file.filename, "room": _room_out(room, existing), "empty_spaces": spaces,
        "message": "" if spaces else "We could not find a good match for this photo. Try a different angle.",
    })


def _room_out(room: dict, existing: set) -> dict:
    return {"type": room["type"], "type_label": _label(room["type"]).title(), "style": room["style"],
            "palette": room["palette"], "summary": room["summary"], "already_has": sorted(existing)}
