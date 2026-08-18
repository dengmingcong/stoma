"""Stream simple docs events。

Generated from OpenAPI: get-events
Streams a bounded Server-Sent Events feed with a simple `type`, `user.id`, `message`, and `timestamp` shape for documentation examples.
"""

from __future__ import annotations

from .models import ErrorModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/events")
class GetEvents(APIRoute[ErrorModel]):
    """Stream simple docs events。
    Streams a bounded Server-Sent Events feed with a simple `type`, `user.id`, `message`, and `timestamp` shape for documentation examples.
    """

    count: int | None = None
    """Number of events to emit"""
