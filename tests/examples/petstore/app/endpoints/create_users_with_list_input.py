"""Creates list of users with given input array.。

Generated from OpenAPI: createUsersWithListInput
Creates list of users with given input array.
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec, RawResponseSpec

from ..models import CreateUsersWithListInputRequest, User
from ..router import router


@router.post("/user/createWithList")
class CreateUsersWithListInput(APIRoute):
    """Creates list of users with given input array.。

    Creates list of users with given input array.
    """

    on_200_application_json: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        status_code=200, media_type="application/json", model=User
    )
    on_200_application_xml: ClassVar[RawResponseSpec[str]] = RawResponseSpec.text(
        status_code=200, media_type="application/xml"
    )
    body: CreateUsersWithListInputRequest
