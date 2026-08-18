"""Redirect a configurable number of times。

Generated from OpenAPI: get-redirect
"""

from __future__ import annotations

from .models import ErrorModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/redirect/{n}")
class GetRedirect(APIRoute[ErrorModel]):
    """Redirect a configurable number of times。"""

    n: int
    """Number of redirects to follow before reaching /get"""
