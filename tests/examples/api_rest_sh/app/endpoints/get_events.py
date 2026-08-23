"""Stream simple docs events。

Generated from OpenAPI: get-events
Streams a bounded Server-Sent Events feed with a simple `type`, `user.id`, `message`, and `timestamp` shape for documentation examples.
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel, GetEventsResponse
from ..router import router


@router.get("/events")
class GetEvents(APIRoute):
    """Stream simple docs events。

    Streams a bounded Server-Sent Events feed with a simple `type`, `user.id`, `message`, and `timestamp` shape for documentation examples.
    """

    count: int | None = None
    """Number of events to emit"""

    @property
    def on_200(self) -> ResponseSpec[GetEventsResponse]:
        return ResponseSpec(
            status_code=200,
            media_type="text/event-stream",
            expected_type=GetEventsResponse,
        )

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200],
            media_type="application/problem+json",
            expected_type=ErrorModel,
        )
