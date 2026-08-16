"""Return request headers。

Generated from OpenAPI: get-headers
"""

from __future__ import annotations

from .models import GetHeadersResponse
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/headers")
class GetHeaders(APIRoute[GetHeadersResponse]):
    """Return request headers。
    """
