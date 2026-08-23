"""Returns pet inventories by status.。

Generated from OpenAPI: getInventory
Returns a map of status codes to quantities.
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import GetInventoryResponse
from ..router import router


@router.get("/store/inventory")
class GetInventory(APIRoute):
    """Returns pet inventories by status.。

    Returns a map of status codes to quantities.
    """

    @property
    def on_200(self) -> ResponseSpec[GetInventoryResponse]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=GetInventoryResponse)
