"""Patch a sample item。

Generated from OpenAPI: patch-item
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, Item, PatchItemRequest
from ..router import router


@router.patch("/items/{item-id}")
class PatchItem(APIRoute):
    """Patch a sample item。"""

    item_id: Annotated[str, Field(serialization_alias="item-id")]
    """Item identifier"""
    body: PatchItemRequest

    @property
    def on_200(self) -> JSONResponseSpec[Item]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=Item)

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
