"""Stream server metrics。

Generated from OpenAPI: get-sse-metrics
Streams simulated server metrics as a [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events) (SSE) stream. Each event is a JSON object with CPU, memory, connection, and request-rate fields sampled from a random walk to mimic real telemetry.
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/sse/metrics")
class GetSseMetrics(APIRoute):
    """Stream server metrics。

    Streams simulated server metrics as a [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events) (SSE) stream. Each event is a JSON object with CPU, memory, connection, and request-rate fields sampled from a random walk to mimic real telemetry.
    """

    count: int | None = None
    """Number of metric events to emit before closing the stream"""

    @property
    def on_200(self) -> ResponseSpec[str]:
        return ResponseSpec(status_code=200, media_type="text/event-stream", expected_type=str)

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", expected_type=ErrorModel
        )
