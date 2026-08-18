"""Return request headers。

Generated from OpenAPI: get-headers
"""

from __future__ import annotations

from .models import GetHeadersResponse, ErrorModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/headers")
class GetHeaders(APIRoute[GetHeadersResponse | ErrorModel]):
    """Return request headers。"""
