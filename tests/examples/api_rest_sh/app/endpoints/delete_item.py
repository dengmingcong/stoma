"""Delete a sample item。

Generated from OpenAPI: delete-item
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from stoma import APIRoute

from ..models import ErrorModel
from ..router import router


@router.delete("/items/{item-id}")
class DeleteItem(APIRoute[ErrorModel]):
    """Delete a sample item。"""

    item_id: Annotated[str, Field(serialization_alias="item-id")]
    """Item identifier"""
