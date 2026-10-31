from fastapi import APIRouter, HTTPException, Depends
from app.core.security import get_current_user


router = APIRouter(prefix="/me", tags=["Me"])

@router.get("/")
def me(current_user=Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "avatar_url": current_user.avatar_url,
        "phone": current_user.phone,
        "address": current_user.address,
    }