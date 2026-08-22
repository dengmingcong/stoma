"""Stream server metrics。

Generated from OpenAPI: get-sse-metrics
Streams simulated server metrics as a [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events) (SSE) stream. Each event is a JSON object with CPU, memory, connection, and request-rate fields sampled from a random walk to mimic real telemetry.
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec, RawResponseSpec

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
    def on_200(self) -> RawResponseSpec[str]:
        return RawResponseSpec(status_code=200, media_type="text/event-stream", target_type=str)

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
