"""get-book。

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
    """get-book。"""

    book_id: Annotated[str, Field(serialization_alias="book-id")]
    """Book identifier"""
    if_match: Annotated[list[str] | None, Header(), Field(serialization_alias="If-Match")] = None
    """Succeeds if the server's resource matches one of the passed values."""
    if_none_match: Annotated[list[str] | None, Header(), Field(serialization_alias="If-None-Match")] = None
    """Succeeds if the server's resource matches none of the passed values. On writes, the special value * may be used to match any existing value."""
    if_modified_since: Annotated[str | None, Header(), Field(serialization_alias="If-Modified-Since")] = None
    """Succeeds if the server's resource date is more recent than the passed date."""
    if_unmodified_since: Annotated[str | None, Header(), Field(serialization_alias="If-Unmodified-Since")] = None
    """Succeeds if the server's resource date is older or the same as the passed date."""
