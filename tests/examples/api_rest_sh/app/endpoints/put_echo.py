from __future__ import annotations

from typing import Annotated

from pydantic import Field

from stoma import APIRoute, Header

from ..models import EchoModel, ErrorModel
from ..router import router


@router.put("/")
class PutEcho(APIRoute[EchoModel | ErrorModel]):
    status: int | None = None
    """Status code to return"""
    if_match: Annotated[list[str] | None, Header(), Field(serialization_alias="If-Match")] = None
    """Succeeds if the server's resource matches one of the passed values."""
    if_none_match: Annotated[list[str] | None, Header(), Field(serialization_alias="If-None-Match")] = None
    """Succeeds if the server's resource matches none of the passed values. On writes, the special value * may be used to match any existing value."""
    if_modified_since: Annotated[str | None, Header(), Field(serialization_alias="If-Modified-Since")] = None
    """Succeeds if the server's resource date is more recent than the passed date."""
    if_unmodified_since: Annotated[str | None, Header(), Field(serialization_alias="If-Unmodified-Since")] = None
    """Succeeds if the server's resource date is older or the same as the passed date."""
