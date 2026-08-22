"""Redirect a configurable number of times。

Generated from OpenAPI: get-relative-redirect
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/relative-redirect/{n}")
class GetRelativeRedirect(APIRoute):
    """Redirect a configurable number of times。"""

    n: int
    """Number of redirects to follow before reaching /get"""

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [302], media_type="application/problem+json", model=ErrorModel
        )
