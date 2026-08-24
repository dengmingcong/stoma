"""Returns pet inventories by status.。

Generated from OpenAPI: getInventory
Returns a map of status codes to quantities.
"""

from __future__ import annotations

from stoma import APIRoute, EmptyResponseSpec, ResponseSpec

from ..models import GetInventoryResponse
from ..router import router


@router.get("/store/inventory")
class GetInventory(APIRoute):
    """Returns pet inventories by status.。

    Returns a map of status codes to quantities.
    """

    @property
    def on_200(self) -> ResponseSpec[GetInventoryResponse]:
        return ResponseSpec(
            status_code=200,
            media_type="application/json",
            expected_type=GetInventoryResponse,
        )

    @property
    def on_default(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=lambda c: c not in [200],
        )
