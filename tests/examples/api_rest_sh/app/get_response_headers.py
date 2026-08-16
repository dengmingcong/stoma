"""Set response headers from query parameters。

Generated from OpenAPI: get-response-headers
"""

from __future__ import annotations

from .models import GetResponseHeadersResponse
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/response-headers")
class GetResponseHeaders(APIRoute[GetResponseHeadersResponse]):
    """Set response headers from query parameters。
    """
