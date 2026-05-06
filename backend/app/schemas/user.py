from datetime import datetime
from pydantic import BaseModel, Field

class UserBase(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="密码，至少8个字符")

class UserResponse(UserBase):
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True