"""Return the User-Agent header。

Generated from OpenAPI: get-user-agent
"""

from __future__ import annotations

from .models import GetUserAgentResponse, ErrorModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/user-agent")
class GetUserAgent(APIRoute[GetUserAgentResponse | ErrorModel]):
    """Return the User-Agent header。
    """
