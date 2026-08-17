"""Patch book。

Generated from OpenAPI: patch-book
Partial update operation supporting both JSON Merge Patch & JSON Patch updates.
"""

from __future__ import annotations

from .models import ErrorModel, PatchBookRequest
from typing import Annotated
from pydantic import Field
from stoma import APIRouter, APIRoute, Header, Body

router = APIRouter()


@router.patch("/books/{book-id}")
class PatchBook(APIRoute[ErrorModel]):
    """Patch book。
    Partial update operation supporting both JSON Merge Patch & JSON Patch updates.
    """
    book_id: Annotated[str, Field(serialization_alias='book-id')]
    if_match: Annotated[list[str] | None, Header(), Field(serialization_alias='If-Match')] = None
    if_none_match: Annotated[list[str] | None, Header(), Field(serialization_alias='If-None-Match')] = None
    if_modified_since: Annotated[str | None, Header(), Field(serialization_alias='If-Modified-Since')] = None
    if_unmodified_since: Annotated[str | None, Header(), Field(serialization_alias='If-Unmodified-Since')] = None
    body: PatchBookRequest
