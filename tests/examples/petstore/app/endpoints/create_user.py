"""Create user.。

Generated from OpenAPI: createUser
This can only be done by the logged in user.
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec, RawResponseSpec

from ..models import User
from ..router import router


@router.post("/user")
class CreateUser(APIRoute):
    """Create user.。

    This can only be done by the logged in user.
    """

    on_200_application_json: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        status_code=200, media_type="application/json", model=User
    )
    on_200_application_xml: ClassVar[RawResponseSpec[str]] = RawResponseSpec.text(
        status_code=200, media_type="application/xml"
    )
    body: User
