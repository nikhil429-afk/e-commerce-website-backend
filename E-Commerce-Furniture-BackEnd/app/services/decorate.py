from fastapi import (APIRouter, UploadFile, File, HTTPException )
from sqlalchemy.orm import Session
from app.schema.product import Product, Images
from app.core.database import get_db
from fastapi import Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from google.genai import types
from dotenv import load_dotenv
import os, io, uuid, json
from google import genai
from typing import List
from PIL import Image
import traceback

load_dotenv()


router = APIRouter(prefix="/ai-decorate", tags=["AI-Vision"])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "assets/")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def gemini_client():
    api_key = os.getenv("GOOGLE_API_KEY")
    # print("API Key:", api_key)
    if not api_key:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY Not Found!")
    return genai.Client(api_key=api_key)

class RecommendedProduct(BaseModel):
    product_id: int
    name: str
    category: str
    image: str
    price: int
    rating: int
    confidence: int
    reason: str

class EmptySpace(BaseModel):
    space_description: str
    box_2d: List[int]
    recommended_products: List[RecommendedProduct]

class RoomAnalysisResponse(BaseModel):
    success: bool
    filename: str
    empty_spaces: List[EmptySpace]

@router.post("", response_model=RoomAnalysisResponse)
async def upload_room(file: UploadFile = File(...), db: Session = Depends(get_db)):
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

        room_image = Image.open(io.BytesIO(image_bytes))

        client = gemini_client()
        products = (db.query(Product, Images).join(Images, Images.product_id == Product.id).filter(Product.in_stock == True).all())

        catalog = []
        for product, product_image in products:

            catalog.append({
                "product_id": product.id,
                "name": product.name,
                "category": product.category,
                "price": product.price,
                "rating": product.rating,
                "image": product_image.file_path,
                "description": product.description,
            })

        prompt = f"""
        You are an expert interior designer and furniture recommendation assistant.
        Your job is to recommend the products ONLY from the provided product catalog.
        Here is the product catalog:
        {json.dumps(catalog, indent=2)}
        
        IMPORTANT RULES:
        1. Recommend ONLY products that exist in the provided catalog.
        2. Never invent product IDs.
        3. Never invent products.
        4. Never recommend products outside the catalog.
        5. Every recommended product_id MUST exist in the catalog.
        6. If no suitable product exists, return an empty recommended_products array.
        7. Image which you are analysing should be a valid room with empty space.
        8. Return nothing if image is not a valid room type with empty space in it.
        
        Analyze the uploaded room image carefully.
        
        Determine:
        - Room type
        - Estimated room size
        - Existing furniture
        - Interior design style
        - Wall colour
        - Floor colour
        - Lighting
        - Color harmony
        - Furniture arrangement
        - Walking space
        
    Detect every empty space where new furniture can reasonably be placed.
    
    For every detected empty space:
    1. Describe the location.
    2. Determine which furniture category fits best.
    3. Compare every product in the provided catalog.
    4. Select the best matching products.
    5. Recommend between 3 and 5 products.
    6. Explain why each product was selected.
    7. Avoid overcrowding.
    8. Leave sufficient walking space.
    9. Consider room style, color harmony and furniture compatibility.
    10. Do not recommend a single product more than once.
    
    Return ONLY valid JSON.
    
    Expected JSON format:
    {{
        "empty_spaces": [
            {{
                "space_description": "",
                "box_2d": [ymin, xmin, ymax, xmax],
                "recommended_products": [
                    {{
                        "product_id": 1,
                        "name": chair,
                        "price": 500,
                        "image": sofa.jpg,
                        "rating": 5,
                        "category": sofa,
                        "confidence": 100,
                        "reason": ""
                    }}
                ]
            }}
        ]
    }}
    
    Rules:
    - Return ONLY JSON.
    - Do NOT use Markdown.
    - Do NOT wrap JSON inside ``` blocks.
    - Do NOT add explanations.
    - Do NOT add extra text.
    - Confidence must be an integer between 60 and 100.
    - Recommend at least 3 and at most 5 products per empty space.
    - If same room type image is found then, recommend different products everytime.
    - If no empty space exists, return:
    
    {{
        "empty_spaces": []
    }}
    """

        response = client.models.generate_content(model="gemini-3.6-flash", contents=[room_image, prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2)
        )
        # print("Gemini Response:", response.text)
        analysis = json.loads(response.text)

        if "empty_spaces" not in analysis:
            raise HTTPException(status_code=500, detail="Gemini did not return empty_spaces.")

        return JSONResponse(status_code=200, content={"success": True, "filename": filename, "empty_spaces": analysis["empty_spaces"]})

    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Gemini returned invalid JSON response")
    
    except Exception as e:
        # traceback.print_exc()
        # print("Exception:", repr(e))
        raise HTTPException(status_code=500, detail=str(e))
    
