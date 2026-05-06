from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel

T = TypeVar('T')

class Response(BaseModel, Generic[T]):
    success: bool = True
    code: int = 200
    data: Optional[T] = None
    message: str = "操作成功"

class ErrorResponse(BaseModel):
    success: bool = False
    code: int = 500
    error: dict

class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    items: List[T]
    total: int
    page: int
    page_size: int
