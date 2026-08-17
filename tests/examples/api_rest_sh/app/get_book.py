"""None。

Generated from OpenAPI: get-book
"""

from __future__ import annotations

from .models import Book, ErrorModel
from typing import Annotated
from pydantic import Field
from stoma import APIRouter, APIRoute, Header

router = APIRouter()


@router.get("/books/{book-id}")
class GetBook(APIRoute[Book | ErrorModel]):
    """None。
    """
    book_id: Annotated[str, Field(serialization_alias='book-id')]
    if_match: Annotated[list[str] | None, Header(), Field(serialization_alias='If-Match')] = None
    if_none_match: Annotated[list[str] | None, Header(), Field(serialization_alias='If-None-Match')] = None
    if_modified_since: Annotated[str | None, Header(), Field(serialization_alias='If-Modified-Since')] = None
    if_unmodified_since: Annotated[str | None, Header(), Field(serialization_alias='If-Unmodified-Since')] = None
