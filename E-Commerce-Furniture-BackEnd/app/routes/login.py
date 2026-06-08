from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext

from app.core.database import get_db
from app.schema.register import User
from app.core.security import create_access_token, create_refresh_token


router = APIRouter(prefix="/login", tags=["Login"])


class LoginRequest(BaseModel):
    email: EmailStr
    pwd: str

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


@router.post("/")
def login(data: LoginRequest, db: Session = Depends(get_db)):

    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        raise HTTPException(status_code=400, detail="User not Found")

    if not verify_password(data.pwd, user.password):
        raise HTTPException(status_code=401, detail="Wrong Password")

    access_token = create_access_token({"id": user.id, "username": user.username, "email": user.email, "role": user.role})

    refresh_token = create_refresh_token({"id": user.id, "username": user.username, "email": user.email, "role": user.role})

    return {
        "message": "Login Successful",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "role": user.role,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }