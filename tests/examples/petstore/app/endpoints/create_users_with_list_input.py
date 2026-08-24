"""Creates list of users with given input array.。

Generated from OpenAPI: createUsersWithListInput
Creates list of users with given input array.
"""

from __future__ import annotations

from stoma import APIRoute, EmptyResponseSpec, ResponseSpec

from ..models import CreateUsersWithListInputRequest, User
from ..router import router


@router.post("/user/createWithList")
class CreateUsersWithListInput(APIRoute):
    """Creates list of users with given input array.。

    Creates list of users with given input array.
    """

    body: CreateUsersWithListInputRequest

    @property
    def on_200_application_json(self) -> ResponseSpec[User]:
        return ResponseSpec(
            status_code=200,
            media_type="application/json",
            expected_type=User,
        )

    @property
    def on_200_application_xml(self) -> ResponseSpec[User]:
        return ResponseSpec(
            status_code=200,
            media_type="application/xml",
            expected_type=User,
        )

    @property
    def on_default(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=lambda c: c not in [200],
        )
