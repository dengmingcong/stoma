"""Delete user resource.。

Generated from OpenAPI: deleteUser
This can only be done by the logged in user.
"""

from __future__ import annotations

from stoma import APIRoute, EmptyResponseSpec

from ..router import router


@router.delete("/user/{username}")
class DeleteUser(APIRoute):
    """Delete user resource.。

    This can only be done by the logged in user.
    """

    username: str
    """The name that needs to be deleted"""

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
