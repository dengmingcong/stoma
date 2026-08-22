"""Patch a sample item。

Generated from OpenAPI: patch-item
"""

from __future__ import annotations

from typing import Annotated, ClassVar

from pydantic import Field

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, Item, PatchItemRequest
from ..router import router


@router.patch("/items/{item-id}")
class PatchItem(APIRoute):
    """Patch a sample item。"""

    on_200: ClassVar[JSONResponseSpec] = JSONResponseSpec(status_code=200, media_type="application/json", model=Item)
    on_default: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
    item_id: Annotated[str, Field(serialization_alias="item-id")]
    """Item identifier"""
    body: PatchItemRequest
