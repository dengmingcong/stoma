"""List sample items。

Generated from OpenAPI: list-items
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, ListItemsResponse
from ..router import router


@router.get("/items")
class ListItems(APIRoute):
    """List sample items。"""

    on_200: ClassVar[JSONResponseSpec[ListItemsResponse]] = JSONResponseSpec(
        status_code=200, media_type="application/json", model=ListItemsResponse
    )
    on_default: ClassVar[JSONResponseSpec[ErrorModel]] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
