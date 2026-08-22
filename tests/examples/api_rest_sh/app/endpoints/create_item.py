"""Create a sample item。

Generated from OpenAPI: create-item
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, Item
from ..router import router


@router.post("/items")
class CreateItem(APIRoute):
    """Create a sample item。"""

    on_200: ClassVar[JSONResponseSpec] = JSONResponseSpec(status_code=200, media_type="application/json", model=Item)
    on_default: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
    body: Item
