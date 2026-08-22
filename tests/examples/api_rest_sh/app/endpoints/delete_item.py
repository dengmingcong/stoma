"""Delete a sample item。

Generated from OpenAPI: delete-item
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel
from ..router import router


@router.delete("/items/{item-id}")
class DeleteItem(APIRoute):
    """Delete a sample item。"""

    item_id: Annotated[str, Field(serialization_alias="item-id")]
    """Item identifier"""

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [204], media_type="application/problem+json", model=ErrorModel
        )
