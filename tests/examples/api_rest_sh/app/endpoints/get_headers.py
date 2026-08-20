"""Return request headers。

Generated from OpenAPI: get-headers
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import ErrorModel, GetHeadersResponse
from ..router import router


@router.get("/headers")
class GetHeaders(APIRoute[GetHeadersResponse | ErrorModel]):
    """Return request headers。"""
