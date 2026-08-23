"""Redirect a configurable number of times。

Generated from OpenAPI: get-redirect
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/redirect/{n}")
class GetRedirect(APIRoute):
    """Redirect a configurable number of times。"""

    n: int
    """Number of redirects to follow before reaching /get"""

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [302], media_type="application/problem+json", expected_type=ErrorModel
        )
