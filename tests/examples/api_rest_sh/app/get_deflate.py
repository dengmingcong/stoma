"""Return an explicitly compressed response。

Generated from OpenAPI: get-deflate
"""

from __future__ import annotations

from .models import ErrorModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/deflate")
class GetDeflate(APIRoute[ErrorModel]):
    """Return an explicitly compressed response。"""
