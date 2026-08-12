from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from app.core.database import get_db
from app.schema.register import User
from app.core.security import create_access_token
from app.core.config import OWNER_NAME, OWNER_EMAIL, OWNER_PASSWORD


router = APIRouter(prefix="/login", tags=["Login"])


class LoginRequest(BaseModel):
    email: EmailStr
    pwd: str

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str):
    return pwd_context.hash(password)


@router.post("/")
def login(data: LoginRequest, db: Session = Depends(get_db)):

    if data.email == OWNER_EMAIL and data.pwd == OWNER_PASSWORD:

        owner_user = db.query(User).filter(User.email == OWNER_EMAIL).first()

        if not owner_user:
            owner_user = User(
                username=OWNER_NAME,
                email=OWNER_EMAIL,
                password=hash_password(OWNER_PASSWORD),
                role="owner",
            )
            db.add(owner_user)
            db.commit()
            db.refresh(owner_user)

        elif owner_user.role != "owner":
            owner_user.role = "owner"
            db.commit()
            db.refresh(owner_user)

        access_token = create_access_token({"id": owner_user.id, "username": owner_user.username, "email": owner_user.email, "role": owner_user.role})

        return {
            "message": "Login Successful",
            "access_token": access_token,
            "role": owner_user.role,
            "user": {
                "id": owner_user.id,
                "username": owner_user.username,
                "email": owner_user.email,
                "role": owner_user.role
            }
        }

    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        raise HTTPException(status_code=400, detail= {"email": "User not Found"})

    if not verify_password(data.pwd, user.password):
        raise HTTPException(status_code=401, detail= {"pwd": "Wrong Password"})

    access_token = create_access_token({"id": user.id, "username": user.username, "email": user.email, "role": user.role})


    return {
        "message": "Login Successful",
        "access_token": access_token,
        "role": user.role,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }

