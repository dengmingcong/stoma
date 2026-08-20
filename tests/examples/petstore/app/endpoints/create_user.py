"""Create user.。

Generated from OpenAPI: createUser
This can only be done by the logged in user.
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import User
from ..router import router


@router.post("/user")
class CreateUser(APIRoute[User]):
    """Create user.。

    This can only be done by the logged in user.
    """

    body: User
