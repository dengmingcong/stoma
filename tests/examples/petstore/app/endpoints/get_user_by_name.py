"""Get user by user name.。

Generated from OpenAPI: getUserByName
Get user detail based on username.
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import User
from ..router import router


@router.get("/user/{username}")
class GetUserByName(APIRoute[User]):
    """Get user by user name.。

    Get user detail based on username.
    """

    username: str
    """The name that needs to be fetched. Use user1 for testing"""
