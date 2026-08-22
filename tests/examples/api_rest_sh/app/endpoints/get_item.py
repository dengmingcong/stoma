"""Get a sample item。

Generated from OpenAPI: get-item
"""

from __future__ import annotations

from typing import Annotated, ClassVar

from pydantic import Field

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, Item
from ..router import router


@router.get("/items/{item-id}")
class GetItem(APIRoute):
    """Get a sample item。"""

    on_200: ClassVar[JSONResponseSpec[Item]] = JSONResponseSpec(
        status_code=200, media_type="application/json", model=Item
    )
    on_default: ClassVar[JSONResponseSpec[ErrorModel]] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
    item_id: Annotated[str, Field(serialization_alias="item-id")]
    """Item identifier"""
