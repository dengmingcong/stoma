"""Place an order for a pet.。

Generated from OpenAPI: placeOrder
Place a new order in the store.
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import Order

router = APIRouter()


@router.post("/store/order")
class PlaceOrder(APIRoute[Order]):
    """Place an order for a pet.。

    Place a new order in the store.
    """

    body: Order
