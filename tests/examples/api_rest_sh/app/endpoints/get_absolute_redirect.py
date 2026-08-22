"""Redirect a configurable number of times。

Generated from OpenAPI: get-absolute-redirect
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/absolute-redirect/{n}")
class GetAbsoluteRedirect(APIRoute):
    """Redirect a configurable number of times。"""

    on_default: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
    n: int
    """Number of redirects to follow before reaching /get"""
