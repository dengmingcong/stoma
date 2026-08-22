"""Returns pet inventories by status.。

Generated from OpenAPI: getInventory
Returns a map of status codes to quantities.
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import GetInventoryResponse
from ..router import router


@router.get("/store/inventory")
class GetInventory(APIRoute):
    """Returns pet inventories by status.。

    Returns a map of status codes to quantities.
    """

    on_200: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        status_code=200, media_type="application/json", model=GetInventoryResponse
    )
