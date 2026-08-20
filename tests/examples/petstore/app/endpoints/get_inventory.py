"""Returns pet inventories by status.。

Generated from OpenAPI: getInventory
Returns a map of status codes to quantities.
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import GetInventoryResponse
from ..router import router


@router.get("/store/inventory")
class GetInventory(APIRoute[GetInventoryResponse]):
    """Returns pet inventories by status.。

    Returns a map of status codes to quantities.
    """
