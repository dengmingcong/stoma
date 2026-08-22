"""Return the parsed request body。

Generated from OpenAPI: post-body
Echo the parsed request body as the complete response body.
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, PostBodyRequest
from ..router import router


@router.post("/body")
class PostBody(APIRoute):
    """Return the parsed request body。

    Echo the parsed request body as the complete response body.
    """

    on_default: ClassVar[JSONResponseSpec[ErrorModel]] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
    body: PostBodyRequest
