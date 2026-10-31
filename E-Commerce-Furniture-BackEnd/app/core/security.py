from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt, ExpiredSignatureError
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader
from datetime import datetime, timedelta
import bcrypt
from app.schema.register import User
from app.core.database import get_db
from sqlalchemy.orm import Session
from app.core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES


security = HTTPBearer()



API_KEY_NAME = "GOOGLE_API_KEY"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)      # <--- This is the API KEY's header name


def hash_password(password: str) -> str:
    # bcrypt only looks at the first 72 bytes
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed) -> bool:
    """Never raises: accounts without a password (Google sign-in) or bad hashes just fail."""
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:72], hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token Expired")
    except JWTError as e:
        raise HTTPException(status_code=401, detail=str(e))


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    payload = verify_token(token)

    user_id = payload.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def require_owner(current_user=Depends(get_current_user)):
    if current_user.role != "owner":
        raise HTTPException(status_code=403, detail="Owner Access Only")
    return current_user


async def verify_api_key(api_key: str = Depends(api_key_header)):
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid or Missing API KEY")
    return api_key