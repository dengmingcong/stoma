"""Create a sample item。

Generated from OpenAPI: create-item
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel, Item
from ..router import router


@router.post("/items")
class CreateItem(APIRoute):
    """Create a sample item。"""

    body: Item

    @property
    def on_200(self) -> ResponseSpec[Item]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=Item)

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", expected_type=ErrorModel
        )
