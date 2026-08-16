"""None。

Generated from OpenAPI: put-book
"""

from __future__ import annotations

from .models import Book
from typing import Annotated
from pydantic import Field
from stoma import APIRouter, APIRoute, Header, Body

router = APIRouter()


@router.put("/books/{book-id}")
class PutBook(APIRoute):
    """None。
    """
    book_id: Annotated[str, Field(serialization_alias='book-id')]
    if_match: Annotated[list[str] | None, Header(), Field(serialization_alias='If-Match')] = None
    if_none_match: Annotated[list[str] | None, Header(), Field(serialization_alias='If-None-Match')] = None
    if_modified_since: Annotated[str | None, Header(), Field(serialization_alias='If-Modified-Since')] = None
    if_unmodified_since: Annotated[str | None, Header(), Field(serialization_alias='If-Unmodified-Since')] = None
    body: Book
