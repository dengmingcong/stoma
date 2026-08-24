"""Get user by user name.。

Generated from OpenAPI: getUserByName
Get user detail based on username.
"""

from __future__ import annotations

from stoma import APIRoute, EmptyResponseSpec, ResponseSpec

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
    def on_400(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=400,
        )

    @property
    def on_404(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=404,
        )

    @property
    def on_default(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=lambda c: c not in [200, 400, 404],
        )
