"""Stream server metrics。

Generated from OpenAPI: get-sse-metrics
Streams simulated server metrics as a [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events) (SSE) stream. Each event is a JSON object with CPU, memory, connection, and request-rate fields sampled from a random walk to mimic real telemetry.
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import ErrorModel

router = APIRouter()


@router.get("/sse/metrics")
class GetSseMetrics(APIRoute[ErrorModel]):
    """Stream server metrics。
    Streams simulated server metrics as a [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events) (SSE) stream. Each event is a JSON object with CPU, memory, connection, and request-rate fields sampled from a random walk to mimic real telemetry.
    """

    count: int | None = None
