"""None。

Generated from OpenAPI: put-types-example
Example write for edits
"""

from __future__ import annotations

from .models import EchoModel, ErrorModel
from typing import Annotated
from pydantic import Field
from stoma import APIRouter, APIRoute, Header

router = APIRouter()


@router.put("/types")
class PutTypesExample(APIRoute[EchoModel | ErrorModel]):
    """None。
    Example write for edits
    """
    status: int | None = None
    if_match: Annotated[list[str] | None, Header(), Field(serialization_alias='If-Match')] = None
    if_none_match: Annotated[list[str] | None, Header(), Field(serialization_alias='If-None-Match')] = None
    if_modified_since: Annotated[str | None, Header(), Field(serialization_alias='If-Modified-Since')] = None
    if_unmodified_since: Annotated[str | None, Header(), Field(serialization_alias='If-Unmodified-Since')] = None
