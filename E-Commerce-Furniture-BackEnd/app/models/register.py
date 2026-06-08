from pydantic import BaseModel
from pydantic import BaseModel, EmailStr

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    
    class Config:
        from_attributes = True

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    pwd: str
    conf_pwd: str
