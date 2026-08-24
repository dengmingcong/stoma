"""Patch book。

Generated from OpenAPI: patch-book
Partial update operation supporting both JSON Merge Patch & JSON Patch updates.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from stoma import APIRoute, EmptyResponseSpec, Header, ResponseSpec

from ..models import ErrorModel, PatchBookRequest
from ..router import router


@router.patch("/books/{book-id}")
class PatchBook(APIRoute):
    """Patch book。

    Partial update operation supporting both JSON Merge Patch & JSON Patch updates.
    """

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
    body: PatchBookRequest

    @property
    def on_204(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=204,
        )

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [204],
            media_type="application/problem+json",
            expected_type=ErrorModel,
        )
