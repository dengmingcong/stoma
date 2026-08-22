"""List sample items。

Generated from OpenAPI: list-items
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, ListItemsResponse
from ..router import router


@router.get("/items")
class ListItems(APIRoute):
    """List sample items。"""

    @property
    def on_200(self) -> JSONResponseSpec[ListItemsResponse]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=ListItemsResponse)

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
