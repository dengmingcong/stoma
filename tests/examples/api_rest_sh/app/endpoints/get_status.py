"""
Generated from OpenAPI: get-status
Status code example
"""

from __future__ import annotations

from typing import Annotated, ClassVar

from pydantic import Field

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/status/{code}")
class GetStatus(APIRoute):
    """
    Status code example
    """

    on_default: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
    code: int
    """Status code to return"""
    retry_after: Annotated[str | None, Field(serialization_alias="retry-after")] = None
    """Retry-After header value"""
    x_retry_in: Annotated[str | None, Field(serialization_alias="x-retry-in")] = None
    """X-Retry-In header value"""
