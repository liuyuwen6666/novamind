from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ResponseBase(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: T | None = None


def ok(data: Any = None, message: str = "success") -> dict:
    return {"code": 200, "message": message, "data": data}


def fail(message: str, code: int = 400) -> dict:
    return {"code": code, "message": message, "data": None}
