"""Place an order for a pet.。

Generated from OpenAPI: placeOrder
Place a new order in the store.
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import Order
from ..router import router


@router.post("/store/order")
class PlaceOrder(APIRoute):
    """Place an order for a pet.。

    Place a new order in the store.
    """

    on_200: ClassVar[JSONResponseSpec[Order]] = JSONResponseSpec(
        status_code=200, media_type="application/json", model=Order
    )
    body: Order
