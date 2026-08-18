"""Return request headers。

Generated from OpenAPI: get-headers
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import ErrorModel, GetHeadersResponse

router = APIRouter()


@router.get("/headers")
class GetHeaders(APIRoute[GetHeadersResponse | ErrorModel]):
    """Return request headers。"""
