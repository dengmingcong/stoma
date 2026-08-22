"""Get user by user name.。

Generated from OpenAPI: getUserByName
Get user detail based on username.
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec, RawResponseSpec

from ..models import User
from ..router import router


@router.get("/user/{username}")
class GetUserByName(APIRoute):
    """Get user by user name.。

    Get user detail based on username.
    """

    on_200_application_json: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        status_code=200, media_type="application/json", model=User
    )
    on_200_application_xml: ClassVar[RawResponseSpec[str]] = RawResponseSpec.text(
        status_code=200, media_type="application/xml"
    )
    username: str
    """The name that needs to be fetched. Use user1 for testing"""
