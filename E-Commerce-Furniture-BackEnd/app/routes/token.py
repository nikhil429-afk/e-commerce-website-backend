from fastapi import APIRouter, HTTPException
from jose import jwt, JWTError
from app.core.security import SECRET_KEY, ALGORITHM, create_access_token
from app.core.database import get_db
from app.schema.register import User
from fastapi import Depends
from sqlalchemy.orm import Session


router = APIRouter()


@router.post("/refresh")
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid Refresh Token")

        user_id = payload.get("id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        new_access_token = create_access_token({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
        })

        return {"access_token": new_access_token}

    except JWTError as e:
        raise HTTPException(status_code=401, detail=str(e))
