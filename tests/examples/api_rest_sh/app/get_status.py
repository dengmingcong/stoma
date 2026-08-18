"""
Generated from OpenAPI: get-status
Status code example
"""

from __future__ import annotations

from typing import Annotated
from pydantic import Field
from stoma import APIRouter, APIRoute
from .models import ErrorModel

router = APIRouter()


@router.get("/status/{code}")
class GetStatus(APIRoute[ErrorModel]):
    """
    Status code example
    """

    code: int
    """Status code to return"""
    retry_after: Annotated[str | None, Field(serialization_alias="retry-after")] = None
    """Retry-After header value"""
    x_retry_in: Annotated[str | None, Field(serialization_alias="x-retry-in")] = None
    """X-Retry-In header value"""
