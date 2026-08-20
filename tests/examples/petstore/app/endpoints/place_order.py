"""Place an order for a pet.。

Generated from OpenAPI: placeOrder
Place a new order in the store.
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import Order
from ..router import router


@router.post("/store/order")
class PlaceOrder(APIRoute[Order]):
    """Place an order for a pet.。

    Place a new order in the store.
    """

    body: Order
