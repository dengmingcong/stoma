"""Return the requester IP。

Generated from OpenAPI: get-ip
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute
from .models import GetIpResponse, ErrorModel

router = APIRouter()


@router.get("/ip")
class GetIp(APIRoute[GetIpResponse | ErrorModel]):
    """Return the requester IP。"""
