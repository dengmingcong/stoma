"""Stream bytes in chunks。

Generated from OpenAPI: get-stream-bytes
"""

from __future__ import annotations

from .models import ErrorModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/stream-bytes/{n}")
class GetStreamBytes(APIRoute[ErrorModel]):
    """Stream bytes in chunks。"""

    n: int
    """Total number of bytes to stream"""
    chunk_size: int | None = None
    """Maximum bytes written per chunk"""
    seed: int | None = None
    """Optional deterministic seed"""
