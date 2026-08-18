"""Set response headers from query parameters。

Generated from OpenAPI: get-response-headers
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute
from .models import GetResponseHeadersResponse, ErrorModel

router = APIRouter()


@router.get("/response-headers")
class GetResponseHeaders(APIRoute[GetResponseHeadersResponse | ErrorModel]):
    """Set response headers from query parameters。"""
