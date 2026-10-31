from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is missing. Configure it in Render Environment Variables."
    )

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 180)
)

OWNER_NAME = os.getenv("OWNER_NAME", "Owner")
OWNER_EMAIL = (os.getenv("OWNER_EMAIL") or "").strip().lower()
OWNER_PASSWORD = os.getenv("OWNER_PASSWORD")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
GEMINI_FALLBACK_MODELS = [
    m.strip()
    for m in os.getenv(
        "GEMINI_FALLBACK_MODELS",
        "gemini-2.5-flash,gemini-2.0-flash"
    ).split(",")
    if m.strip()
]

EXTRA_CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "").split(",")
    if o.strip()
]

MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_MB", 5)) * 1024 * 1024
MAX_ROOM_IMAGE_BYTES = int(os.getenv("MAX_ROOM_IMAGE_MB", 8)) * 1024 * 1024

if not SECRET_KEY or SECRET_KEY == "your_secret_key_here":
    import warnings
    warnings.warn(
        "SECRET_KEY is missing or still the placeholder.",
        stacklevel=1,
    )
