"""Return the parsed request body。

Generated from OpenAPI: post-body
Echo the parsed request body as the complete response body.
"""

from __future__ import annotations

from .models import PostBodyRequest
from typing import Annotated
from stoma import APIRouter, APIRoute, Body

router = APIRouter()


@router.post("/body")
class PostBody(APIRoute):
    """Return the parsed request body。
    Echo the parsed request body as the complete response body.
    """
    body: PostBodyRequest
