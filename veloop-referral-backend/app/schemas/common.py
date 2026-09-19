from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None


class ErrorResponse(BaseModel):
    success: bool = False
    code: str
    message: str
    maskedEmail: Optional[str] = None


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def ok(data: Any) -> dict:
    return {"success": True, "data": data}
