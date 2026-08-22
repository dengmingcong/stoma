"""Get user by user name.。

Generated from OpenAPI: getUserByName
Get user detail based on username.
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec, RawResponseSpec

from ..models import User
from ..router import router


@router.get("/user/{username}")
class GetUserByName(APIRoute):
    """Get user by user name.。

    Get user detail based on username.
    """

    username: str
    """The name that needs to be fetched. Use user1 for testing"""

    @property
    def on_200_application_json(self) -> JSONResponseSpec[User]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=User)

    @property
    def on_200_application_xml(self) -> RawResponseSpec[str]:
        return RawResponseSpec(status_code=200, media_type="application/xml", target_type=str)
