"""Return request headers。

Generated from OpenAPI: get-headers
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute
from .models import GetHeadersResponse, ErrorModel

router = APIRouter()


@router.get("/headers")
class GetHeaders(APIRoute[GetHeadersResponse | ErrorModel]):
    """Return request headers。"""
