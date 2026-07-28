from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None
    errors: Optional[Any] = None

    model_config = {"from_attributes": True}
