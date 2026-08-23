"""Find purchase order by ID.。

Generated from OpenAPI: getOrderById
For valid response try integer IDs with value <= 5 or > 10. Other values will generate exceptions.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from stoma import APIRoute, EmptyResponseSpec, ResponseSpec

from ..models import Order
from ..router import router


@router.get("/store/order/{orderId}")
class GetOrderById(APIRoute):
    """Find purchase order by ID.。

    For valid response try integer IDs with value <= 5 or > 10. Other values will generate exceptions.
    """

    order_id: Annotated[int, Field(serialization_alias="orderId")]
    """ID of order that needs to be fetched"""

    @property
    def on_200_application_json(self) -> ResponseSpec[Order]:
        return ResponseSpec(
            status_code=200,
            media_type="application/json",
            expected_type=Order,
        )

    @property
    def on_200_application_xml(self) -> ResponseSpec[Order]:
        return ResponseSpec(
            status_code=200,
            media_type="application/xml",
            expected_type=Order,
        )

    @property
    def on_400(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=400,
        )

    @property
    def on_404(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=404,
        )

    @property
    def on_default(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=lambda c: c not in [200, 400, 404],
        )
