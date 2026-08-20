"""Redirect a configurable number of times。

Generated from OpenAPI: get-relative-redirect
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import ErrorModel
from ..router import router


@router.get("/relative-redirect/{n}")
class GetRelativeRedirect(APIRoute[ErrorModel]):
    """Redirect a configurable number of times。"""

    n: int
    """Number of redirects to follow before reaching /get"""
