"""Find purchase order by ID.。

Generated from OpenAPI: getOrderById
For valid response try integer IDs with value <= 5 or > 10. Other values will generate exceptions.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from stoma import APIRoute, APIRouter

from .models import Order

router = APIRouter()


@router.get("/store/order/{orderId}")
class GetOrderById(APIRoute[Order]):
    """Find purchase order by ID.。

    For valid response try integer IDs with value <= 5 or > 10. Other values will generate exceptions.
    """

    order_id: Annotated[int, Field(serialization_alias="orderId")]
    """ID of order that needs to be fetched"""
