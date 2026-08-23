"""Create user.。

Generated from OpenAPI: createUser
This can only be done by the logged in user.
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import User
from ..router import router


@router.post("/user")
class CreateUser(APIRoute):
    """Create user.。

    This can only be done by the logged in user.
    """

    body: User

    @property
    def on_200_application_json(self) -> ResponseSpec[User]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=User)

    @property
    def on_200_application_xml(self) -> ResponseSpec[str]:
        return ResponseSpec(status_code=200, media_type="application/xml", expected_type=str)
