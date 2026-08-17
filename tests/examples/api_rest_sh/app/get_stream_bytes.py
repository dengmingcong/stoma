"""Stream bytes in chunks。

Generated from OpenAPI: get-stream-bytes
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import ErrorModel

router = APIRouter()


@router.get("/stream-bytes/{n}")
class GetStreamBytes(APIRoute[ErrorModel]):
    """Stream bytes in chunks。"""

    n: int
    chunk_size: int | None = None
    seed: int | None = None
