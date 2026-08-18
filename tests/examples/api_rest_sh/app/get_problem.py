"""Return an RFC 7807 problem document。

Generated from OpenAPI: get-problem
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute
from .models import GetProblemResponse, ErrorModel

router = APIRouter()


@router.get("/problem")
class GetProblem(APIRoute[GetProblemResponse | ErrorModel]):
    """Return an RFC 7807 problem document。"""
