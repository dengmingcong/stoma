"""Return an explicitly compressed response。

Generated from OpenAPI: get-deflate
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/deflate")
class GetDeflate(APIRoute):
    """Return an explicitly compressed response。
    """
