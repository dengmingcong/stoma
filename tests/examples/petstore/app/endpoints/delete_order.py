"""Delete purchase order by identifier.。

Generated from OpenAPI: deleteOrder
For valid response try integer IDs with value < 1000. Anything above 1000 or non-integers will generate API errors.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from stoma import APIRoute

from ..router import router


@router.delete("/store/order/{orderId}")
class DeleteOrder(APIRoute):
    """Delete purchase order by identifier.。

    For valid response try integer IDs with value < 1000. Anything above 1000 or non-integers will generate API errors.
    """

    order_id: Annotated[int, Field(serialization_alias="orderId")]
    """ID of the order that needs to be deleted"""
