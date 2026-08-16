"""Return the User-Agent header。

Generated from OpenAPI: get-user-agent
"""

from __future__ import annotations

from .models import GetUserAgentResponse
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/user-agent")
class GetUserAgent(APIRoute[GetUserAgentResponse]):
    """Return the User-Agent header。
    """
