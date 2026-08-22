"""Creates list of users with given input array.。

Generated from OpenAPI: createUsersWithListInput
Creates list of users with given input array.
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec, RawResponseSpec

from ..models import CreateUsersWithListInputRequest, User
from ..router import router


@router.post("/user/createWithList")
class CreateUsersWithListInput(APIRoute):
    """Creates list of users with given input array.。

    Creates list of users with given input array.
    """

    body: CreateUsersWithListInputRequest

    @property
    def on_200_application_json(self) -> JSONResponseSpec[User]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=User)

    @property
    def on_200_application_xml(self) -> RawResponseSpec[str]:
        return RawResponseSpec(status_code=200, media_type="application/xml", target_type=str)
