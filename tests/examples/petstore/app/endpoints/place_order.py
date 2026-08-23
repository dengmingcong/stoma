"""Place an order for a pet.。

Generated from OpenAPI: placeOrder
Place a new order in the store.
"""

from __future__ import annotations

from stoma import APIRoute, EmptyResponseSpec, ResponseSpec

from ..models import Order
from ..router import router


@router.post("/store/order")
class PlaceOrder(APIRoute):
    """Place an order for a pet.。

    Place a new order in the store.
    """

    body: Order

    @property
    def on_200(self) -> ResponseSpec[Order]:
        return ResponseSpec(
            status_code=200,
            media_type="application/json",
            expected_type=Order,
        )

    @property
    def on_400(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=400,
        )

    @property
    def on_422(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=422,
        )

    @property
    def on_default(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=lambda c: c not in [200, 400, 422],
        )
