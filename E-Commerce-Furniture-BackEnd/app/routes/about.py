from fastapi import APIRouter

router = APIRouter(prefix="/about", tags=["about"])


@router.get("/")
def get_about_info():
    return {"Company": "Furniture Store"}

