"""Return the parsed request body。

Generated from OpenAPI: post-body
Echo the parsed request body as the complete response body.
"""

from __future__ import annotations

from stoma import APIRoute, EmptyResponseSpec, ResponseSpec

from ..models import ErrorModel, PostBodyRequest
from ..router import router


@router.post("/body")
class PostBody(APIRoute):
    """Return the parsed request body。

    Echo the parsed request body as the complete response body.
    """

    body: PostBodyRequest

    @property
    def on_200(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=200,
        )

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200],
            media_type="application/problem+json",
            expected_type=ErrorModel,
        )
