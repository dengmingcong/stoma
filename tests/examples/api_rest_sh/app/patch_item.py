"""Patch a sample item。

Generated from OpenAPI: patch-item
"""

from __future__ import annotations

from typing import Annotated
from pydantic import Field
from stoma import APIRouter, APIRoute
from .models import Item, ErrorModel, PatchItemRequest

router = APIRouter()


@router.patch("/items/{item-id}")
class PatchItem(APIRoute[Item | ErrorModel]):
    """Patch a sample item。"""

    item_id: Annotated[str, Field(serialization_alias="item-id")]
    """Item identifier"""
    body: PatchItemRequest
