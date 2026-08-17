"""Delete a sample item。

Generated from OpenAPI: delete-item
"""

from __future__ import annotations

from .models import ErrorModel
from typing import Annotated
from pydantic import Field
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.delete("/items/{item-id}")
class DeleteItem(APIRoute[ErrorModel]):
    """Delete a sample item。
    """
    item_id: Annotated[str, Field(serialization_alias='item-id')]
