from fastapi import (APIRouter, UploadFile, File, HTTPException, Depends )
from app.core.security import verify_api_key
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from google.genai import types
from google import genai
from PIL import Image
import os, io, uuid, json
import traceback

load_dotenv()


router = APIRouter(prefix="/ai-decorate", tags=["AI-Vision"])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "assets/")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def gemini_client():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY Not Found!")
    return genai.Client(api_key=api_key)


@router.post("")
async def upload_room(file: UploadFile = File(...)):
    # print(file.filename)
    # print(os.getenv("GOOGLE_API_KEY"))
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp" ]

    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only JPG, JPEG, PNG and WEBP images are allowed.")
    
    try:
        image_bytes = await file.read()
        extension = file.filename.split(".")[-1]

        filename = f"{uuid.uuid4()}.{extension}"

        file_path = os.path.join(UPLOAD_FOLDER, filename)

        with open(file_path, "wb") as f:
            f.write(image_bytes)

        image = Image.open(io.BytesIO(image_bytes))

        client = gemini_client()

        prompt = """
        Analyze this room image.
        Detect every large empty usable space where furniture can be placed.
        Return ONLY valid JSON.
        
        Format: [
            {
                "description":"Empty floor near sofa",
                "box_2d":[ymin,xmin,ymax,xmax]
            }
        ]
        """

        response = client.models.generate_content(model="gemini-2.5-flash", contents=[image, prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2)
        )

        try:
            analysis = json.loads(response.text)
        except Exception:
            analysis = response.text

        return JSONResponse(status_code=200, content={"success": True, "filename": filename, "analysis": analysis})

    except Exception as e:
        traceback.print_exc()
        print("Error", repr(e))
        raise HTTPException(status_code=500, detail=str(e))