"""Return an RFC 7807 problem document。

Generated from OpenAPI: get-problem
"""

from __future__ import annotations

from .models import GetProblemResponse
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/problem")
class GetProblem(APIRoute[GetProblemResponse]):
    """Return an RFC 7807 problem document。
    """
