"""Get a sample item。

Generated from OpenAPI: get-item
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel, Item
from ..router import router


@router.get("/items/{item-id}")
class GetItem(APIRoute):
    """Get a sample item。"""

    item_id: Annotated[str, Field(serialization_alias="item-id")]
    """Item identifier"""

    @property
    def on_200(self) -> ResponseSpec[Item]:
        return ResponseSpec(
            status_code=200,
            media_type="application/json",
            expected_type=Item,
        )

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200],
            media_type="application/problem+json",
            expected_type=ErrorModel,
        )
