"""Find purchase order by ID.。

Generated from OpenAPI: getOrderById
For valid response try integer IDs with value <= 5 or > 10. Other values will generate exceptions.
"""

from __future__ import annotations

from typing import Annotated, ClassVar

from pydantic import Field

from stoma import APIRoute, JSONResponseSpec, RawResponseSpec

from ..models import Order
from ..router import router


@router.get("/store/order/{orderId}")
class GetOrderById(APIRoute):
    """Find purchase order by ID.。

    For valid response try integer IDs with value <= 5 or > 10. Other values will generate exceptions.
    """

    on_200_application_json: ClassVar[JSONResponseSpec[Order]] = JSONResponseSpec(
        status_code=200, media_type="application/json", model=Order
    )
    on_200_application_xml: ClassVar[RawResponseSpec[str]] = RawResponseSpec.text(
        status_code=200, media_type="application/xml"
    )
    order_id: Annotated[int, Field(serialization_alias="orderId")]
    """ID of order that needs to be fetched"""
