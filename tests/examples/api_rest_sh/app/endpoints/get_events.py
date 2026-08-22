"""Stream simple docs events。

Generated from OpenAPI: get-events
Streams a bounded Server-Sent Events feed with a simple `type`, `user.id`, `message`, and `timestamp` shape for documentation examples.
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec, RawResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/events")
class GetEvents(APIRoute):
    """Stream simple docs events。

    Streams a bounded Server-Sent Events feed with a simple `type`, `user.id`, `message`, and `timestamp` shape for documentation examples.
    """

    on_200: ClassVar[RawResponseSpec[str]] = RawResponseSpec.text(status_code=200, media_type="text/event-stream")
    on_default: ClassVar[JSONResponseSpec[ErrorModel]] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
    count: int | None = None
    """Number of events to emit"""
