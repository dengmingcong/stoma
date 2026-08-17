"""Redirect a configurable number of times。

Generated from OpenAPI: get-absolute-redirect
"""

from __future__ import annotations

from .models import ErrorModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/absolute-redirect/{n}")
class GetAbsoluteRedirect(APIRoute[ErrorModel]):
    """Redirect a configurable number of times。
    """
    n: int
