"""Return an RFC 7807 problem document。

Generated from OpenAPI: get-problem
"""

from __future__ import annotations

from .models import GetProblemResponse, ErrorModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/problem")
class GetProblem(APIRoute[GetProblemResponse | ErrorModel]):
    """Return an RFC 7807 problem document。"""
