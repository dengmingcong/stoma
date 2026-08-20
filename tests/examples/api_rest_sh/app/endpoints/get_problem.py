"""Return an RFC 7807 problem document。

Generated from OpenAPI: get-problem
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import ErrorModel, GetProblemResponse
from ..router import router


@router.get("/problem")
class GetProblem(APIRoute[GetProblemResponse | ErrorModel]):
    """Return an RFC 7807 problem document。"""
