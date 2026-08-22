"""Redirect to a supplied URL。

Generated from OpenAPI: get-redirect-to
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/redirect-to")
class GetRedirectTo(APIRoute):
    """Redirect to a supplied URL。"""

    on_default: ClassVar[JSONResponseSpec[ErrorModel]] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
    url: str
    """Absolute or relative redirect target"""
    status_code: int | None = None
    """3xx redirect status code to send"""
