"""Return the parsed request body。

Generated from OpenAPI: post-body
Echo the parsed request body as the complete response body.
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import ErrorModel, PostBodyRequest
from ..router import router


@router.post("/body")
class PostBody(APIRoute[ErrorModel]):
    """Return the parsed request body。

    Echo the parsed request body as the complete response body.
    """

    body: PostBodyRequest
