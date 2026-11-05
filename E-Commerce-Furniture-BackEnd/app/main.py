from app.routes import (dashboard, product, cart, register, wishlist, order, owner, about, contact, login, charts, profile, notification, media)
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.routes.get_user import router as me_router
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import EXTRA_CORS_ORIGINS
from app.core.owner_seed import seed_owner
from app.core.schema_check import check_user_columns, ensure_appointment_and_notification_schema
from app.core import notify as notify_hub
from starlette.middleware.gzip import GZipMiddleware
from app.services import decorate
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import asyncio
import logging
import os

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "assets", "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    notify_hub.bind_loop(asyncio.get_running_loop())      # lets route handlers push live notifications
    if not check_user_columns():      # logs a clear error if `alembic upgrade head` was forgotten
        seed_owner()          # the owner account always exists and always comes from .env
    ensure_appointment_and_notification_schema()
    yield


app = FastAPI(lifespan=lifespan)


def _error(status_code: int, message: str, **extra):
    """One error shape for the whole API. `detail` is kept because the React app reads it."""
    return JSONResponse(status_code=status_code, content={"detail": message, "message": message, **extra})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    problems = []
    for err in exc.errors():
        field = ".".join(str(p) for p in err.get("loc", []) if p not in ("body", "query", "path"))
        problems.append(f"{field}: {err.get('msg')}" if field else str(err.get("msg")))
    message = "; ".join(problems) or "Validation Error"
    return JSONResponse(status_code=422, content={
        "detail": message,
        "message": "Validation Error",
        "errors": jsonable(exc.errors()),
    })


def jsonable(errors):
    # exc.errors() can contain non-serialisable objects (e.g. the original exception in `ctx`)
    out = []
    for e in errors:
        out.append({"loc": list(e.get("loc", [])), "msg": str(e.get("msg", "")), "type": str(e.get("type", ""))})
    return out


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    # keep dict details ({"email": "..."}) exactly as the login / register forms expect them
    if isinstance(exc.detail, (dict, list)):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=getattr(exc, "headers", None))
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail, "message": exc.detail},
                        headers=getattr(exc, "headers", None))


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    log.warning("Database integrity error on %s %s: %s", request.method, request.url.path, exc.orig)
    return _error(409, "This change conflicts with existing data (for example a duplicate or something still in use).")


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request: Request, exc: SQLAlchemyError):
    log.exception("Database error on %s %s", request.method, request.url.path)
    return _error(503, "The database is temporarily unavailable. Please try again in a moment.")


@app.middleware("http")
async def catch_all_errors(request: Request, call_next):
    """Last safety net: any unexpected crash becomes a clean JSON 500 instead of a dropped
    connection. Registered BEFORE CORSMiddleware so the response still gets CORS headers
    (otherwise the browser reports a confusing 'CORS error' instead of the real message)."""
    try:
        return await call_next(request)
    except Exception:
        log.exception("Unhandled error on %s %s", request.method, request.url.path)
        return _error(500, "Something went wrong on our side. Please try again.")


class SelectiveGZip:
    """Compress JSON responses (the product list shrinks ~5x) but never the live notification stream."""
    def __init__(self, app):
        self.app = app
        self.gzip = GZipMiddleware(app, minimum_size=1024)

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"].endswith("/stream"):
            await self.app(scope, receive, send)
        else:
            await self.gzip(scope, receive, send)


app.add_middleware(SelectiveGZip)

app.add_middleware( CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174", *EXTRA_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(dashboard.router)

app.include_router(owner.router)

app.include_router(register.router)

app.include_router(login.router)

app.include_router(product.router)

class CachedStaticFiles(StaticFiles):
    """Uploaded photos get a random file name and never change, so browsers may keep them for a year."""
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response


app.mount("/uploads", CachedStaticFiles(directory=UPLOAD_DIR), name="uploads")

app.include_router(media.router)

app.include_router(cart.router)

app.include_router(wishlist.router)

app.include_router(about.router)

app.include_router(contact.router)

app.include_router(order.router)

app.include_router(charts.router)

app.include_router(decorate.router)

app.include_router(me_router)

app.include_router(profile.router)

app.include_router(notification.router)


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
