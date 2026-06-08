from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.routes import (dashboard, product, cart, register, wishlist, order, owner, about, contact, login, charts)
from app.routes.token import router as token_router
from app.routes.get_user import router as me_router
from fastapi.staticfiles import StaticFiles
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "assets", "uploads")

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={
        "message": "Validation Error",
        "errors": exc.errors(),
        },
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(token_router)

app.include_router(dashboard.router)

app.include_router(owner.router)

app.include_router(register.router)

app.include_router(login.router)

app.include_router(product.router)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.include_router(cart.router)

app.include_router(wishlist.router)

app.include_router(about.router)

app.include_router(contact.router)

app.include_router(order.router)

app.include_router(charts.router)

app.include_router(me_router)
