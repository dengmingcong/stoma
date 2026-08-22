"""Delete a sample item。

Generated from OpenAPI: delete-item
"""

from __future__ import annotations

from typing import Annotated, ClassVar

from pydantic import Field

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel
from ..router import router


@router.delete("/items/{item-id}")
class DeleteItem(APIRoute):
    """Delete a sample item。"""

    on_default: ClassVar[JSONResponseSpec[ErrorModel]] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
    item_id: Annotated[str, Field(serialization_alias="item-id")]
    """Item identifier"""
