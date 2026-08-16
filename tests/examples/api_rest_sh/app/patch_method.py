"""Echo request data。

Generated from OpenAPI: patch-method
"""

from __future__ import annotations

from .models import EchoModel, PatchMethodRequest
from typing import Annotated
from pydantic import Field
from stoma import APIRouter, APIRoute, Header, Body

router = APIRouter()


@router.patch("/patch")
class PatchMethod(APIRoute[EchoModel]):
    """Echo request data。
    """
    status: int | None = None
    if_match: Annotated[list[str] | None, Header(), Field(serialization_alias='If-Match')] = None
    if_none_match: Annotated[list[str] | None, Header(), Field(serialization_alias='If-None-Match')] = None
    if_modified_since: Annotated[str | None, Header(), Field(serialization_alias='If-Modified-Since')] = None
    if_unmodified_since: Annotated[str | None, Header(), Field(serialization_alias='If-Unmodified-Since')] = None
    body: PatchMethodRequest
