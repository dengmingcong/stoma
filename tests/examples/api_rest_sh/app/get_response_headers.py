"""Set response headers from query parameters。

Generated from OpenAPI: get-response-headers
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import ErrorModel, GetResponseHeadersResponse

router = APIRouter()


@router.get("/response-headers")
class GetResponseHeaders(APIRoute[GetResponseHeadersResponse | ErrorModel]):
    """Set response headers from query parameters。"""
