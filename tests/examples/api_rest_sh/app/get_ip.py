"""Return the requester IP。

Generated from OpenAPI: get-ip
"""

from __future__ import annotations

from .models import GetIpResponse
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/ip")
class GetIp(APIRoute[GetIpResponse]):
    """Return the requester IP。
    """
