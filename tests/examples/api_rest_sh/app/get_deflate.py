"""Return an explicitly compressed response。

Generated from OpenAPI: get-deflate
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute
from .models import ErrorModel

router = APIRouter()


@router.get("/deflate")
class GetDeflate(APIRoute[ErrorModel]):
    """Return an explicitly compressed response。"""
