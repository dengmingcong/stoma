"""Return the User-Agent header。

Generated from OpenAPI: get-user-agent
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute
from .models import GetUserAgentResponse, ErrorModel

router = APIRouter()


@router.get("/user-agent")
class GetUserAgent(APIRoute[GetUserAgentResponse | ErrorModel]):
    """Return the User-Agent header。"""
