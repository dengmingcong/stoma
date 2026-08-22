"""Create user.。

Generated from OpenAPI: createUser
This can only be done by the logged in user.
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec, RawResponseSpec

from ..models import User
from ..router import router


@router.post("/user")
class CreateUser(APIRoute):
    """Create user.。

    This can only be done by the logged in user.
    """

    body: User

    @property
    def on_200_application_json(self) -> JSONResponseSpec[User]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=User)

    @property
    def on_200_application_xml(self) -> RawResponseSpec[str]:
        return RawResponseSpec(status_code=200, media_type="application/xml", target_type=str)
