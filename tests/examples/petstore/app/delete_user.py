"""Delete user resource.。

Generated from OpenAPI: deleteUser
This can only be done by the logged in user.
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

router = APIRouter()


@router.delete("/user/{username}")
class DeleteUser(APIRoute):
    """Delete user resource.。

    This can only be done by the logged in user.
    """

    username: str
    """The name that needs to be deleted"""
