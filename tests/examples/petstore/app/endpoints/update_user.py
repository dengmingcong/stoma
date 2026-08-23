"""Update user resource.。

Generated from OpenAPI: updateUser
This can only be done by the logged in user.
"""

from __future__ import annotations

from stoma import APIRoute, EmptyResponseSpec

from ..models import User
from ..router import router


@router.put("/user/{username}")
class UpdateUser(APIRoute):
    """Update user resource.。

    This can only be done by the logged in user.
    """

    username: str
    """name that need to be deleted"""
    body: User

    @property
    def on_200(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=200,
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
