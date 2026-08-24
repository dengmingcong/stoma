"""List sample items。

Generated from OpenAPI: list-items
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel, ListItemsResponse
from ..router import router


@router.get("/items")
class ListItems(APIRoute):
    """List sample items。"""

    @property
    def on_200(self) -> ResponseSpec[ListItemsResponse]:
        return ResponseSpec(
            status_code=200,
            media_type="application/json",
            expected_type=ListItemsResponse,
        )

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200],
            media_type="application/problem+json",
            expected_type=ErrorModel,
        )
