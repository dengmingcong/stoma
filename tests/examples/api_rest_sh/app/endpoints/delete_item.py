"""Delete a sample item。

Generated from OpenAPI: delete-item
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from stoma import APIRoute, EmptyResponseSpec, ResponseSpec

from ..models import ErrorModel
from ..router import router


@router.delete("/items/{item-id}")
class DeleteItem(APIRoute):
    """Delete a sample item。"""

    item_id: Annotated[str, Field(serialization_alias="item-id")]
    """Item identifier"""

    @property
    def on_204(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=204,
        )

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [204],
            media_type="application/problem+json",
            expected_type=ErrorModel,
        )
