from fastapi import APIRouter, HTTPException, UploadFile, File
from datetime import datetime
import os, uuid

router = APIRouter()

UPLOAD_FOLDER = "app/assets/decorate/uploaded"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@router.post("/ai-decorat")
async def upload_room(file: UploadFile = File(...)):
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only JPG, JPEG, PNG and WEBP images are allowed")

    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(UPLOAD_FOLDER, unique_filename)

    with open(file_path, "wb") as image:
        content = await file.read()
        image.write(content)

    return {
        "success": True,
        "message": "Room Uploaded Successfully",
        "image_name": unique_filename,
        "image_path": file_path
    }