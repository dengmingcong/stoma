"""Get a sample item。

Generated from OpenAPI: get-item
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from stoma import APIRoute, APIRouter

from .models import ErrorModel, Item

router = APIRouter()


@router.get("/items/{item-id}")
class GetItem(APIRoute[Item | ErrorModel]):
    """Get a sample item。"""

    item_id: Annotated[str, Field(serialization_alias="item-id")]
    """Item identifier"""
