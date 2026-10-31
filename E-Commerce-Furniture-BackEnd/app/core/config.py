from dotenv import load_dotenv
import os

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = os.getenv("DATABASE_URL") or (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 180))

OWNER_NAME = os.getenv("OWNER_NAME", "Owner")
# Emails are always compared in lower case (MySQL treats them case-insensitively).
OWNER_EMAIL = (os.getenv("OWNER_EMAIL") or "").strip().lower()
OWNER_PASSWORD = os.getenv("OWNER_PASSWORD")

# Google Sign-In (OAuth "Web application" client id from Google Cloud Console)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()

# Gemini model used by the AI room decorator
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
# Tried in order if the model above is not available for your API key
GEMINI_FALLBACK_MODELS = [m.strip() for m in os.getenv("GEMINI_FALLBACK_MODELS", "gemini-2.5-flash,gemini-2.0-flash").split(",") if m.strip()]

# Extra browser origins allowed by CORS (comma separated), e.g. your deployed site
EXTRA_CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

# Upload limits
MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_MB", 5)) * 1024 * 1024
MAX_ROOM_IMAGE_BYTES = int(os.getenv("MAX_ROOM_IMAGE_MB", 8)) * 1024 * 1024

if not SECRET_KEY or SECRET_KEY == "your_secret_key_here":
    import warnings
    warnings.warn(
        "SECRET_KEY is missing or still the placeholder - anyone can forge login tokens. "
        "Set a long random value in .env (python -c \"import secrets; print(secrets.token_urlsafe(48))\").",
        stacklevel=1,
    )
