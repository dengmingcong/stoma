"""None。

Generated from OpenAPI: patch-echo
"""

from __future__ import annotations

from .models import EchoModel, PatchEchoRequest
from typing import Annotated
from pydantic import Field
from stoma import APIRouter, APIRoute, Header, Body

router = APIRouter()


@router.patch("/")
class PatchEcho(APIRoute[EchoModel]):
    """None。
    """
    status: int | None = None
    if_match: Annotated[list[str] | None, Header(), Field(serialization_alias='If-Match')] = None
    if_none_match: Annotated[list[str] | None, Header(), Field(serialization_alias='If-None-Match')] = None
    if_modified_since: Annotated[str | None, Header(), Field(serialization_alias='If-Modified-Since')] = None
    if_unmodified_since: Annotated[str | None, Header(), Field(serialization_alias='If-Unmodified-Since')] = None
    body: PatchEchoRequest
