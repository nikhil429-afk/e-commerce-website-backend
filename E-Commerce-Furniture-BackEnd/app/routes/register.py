from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.schema.register import User
from app.models.register import RegisterRequest
from passlib.context import CryptContext
from app.core.database import get_db
import re


router = APIRouter(prefix="/register", tags=["register"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)


@router.post('/')
def register(data: RegisterRequest, db: Session = Depends(get_db)):

    error = {}
    username_pattern = r"^[a-zA-Z]{3,50}$"

    if not data.username:
        error["username"] = "Username should not be Empty!"

    elif not re.match(username_pattern, data.username):
        error["username"] = "Username must be 3-50 letters Only!"

    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not data.email:
        error["email"] = "Email should not be Empty!"

    elif not re.match(email_pattern, data.email):
        error["email"] = "Invalid Email Format!"

    OWNER_EMAILS = ["owner@furnisher.com"]

    role = "owner" if data.email in OWNER_EMAILS else "user"

    password_pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[A-Za-z\d@$#%!]{8,15}$"

    if not data.pwd:
        error["pwd"] = "Password should not be Empty!"

    elif not re.match(password_pattern, data.pwd):
        error["pwd"] = ("Password must contain Uppercase," "Lowercase, Number. (8-15 Characters)!")

    if data.pwd != data.conf_pwd:
        error["conf_pwd"] = "Passwords didn't Match!"

    if error:
        raise HTTPException(status_code=400, detail=error)

    try:
        existing_user = (db.query(User) .filter(User.email == data.email) .first())

        if existing_user:
            raise HTTPException(status_code=400, detail={"email": "This Email is already Registered!"})

        hashed_password = hash_password(data.pwd)
        new_user = User(username=data.username, email=data.email, password=hashed_password, role=role)

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {"message": f"{data.username} Registration Successful!"}

    except HTTPException as e:
        raise e

    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Internal Server Error!")