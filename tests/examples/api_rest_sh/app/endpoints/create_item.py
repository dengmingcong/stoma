"""Create a sample item。

Generated from OpenAPI: create-item
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, Item
from ..router import router


@router.post("/items")
class CreateItem(APIRoute):
    """Create a sample item。"""

    body: Item

    @property
    def on_200(self) -> JSONResponseSpec[Item]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=Item)

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
