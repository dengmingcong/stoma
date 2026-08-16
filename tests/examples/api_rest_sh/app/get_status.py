"""None。

Generated from OpenAPI: get-status
Status code example
"""

from __future__ import annotations

from typing import Annotated
from pydantic import Field
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/status/{code}")
class GetStatus(APIRoute):
    """None。
    Status code example
    """
    code: int
    retry_after: Annotated[str | None, Field(serialization_alias='retry-after')] = None
    x_retry_in: Annotated[str | None, Field(serialization_alias='x-retry-in')] = None
