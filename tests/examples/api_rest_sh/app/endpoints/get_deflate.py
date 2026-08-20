"""Return an explicitly compressed response。

Generated from OpenAPI: get-deflate
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import ErrorModel
from ..router import router


@router.get("/deflate")
class GetDeflate(APIRoute[ErrorModel]):
    """Return an explicitly compressed response。"""
