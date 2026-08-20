"""Update user resource.。

Generated from OpenAPI: updateUser
This can only be done by the logged in user.
"""

from __future__ import annotations

from stoma import APIRoute

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
