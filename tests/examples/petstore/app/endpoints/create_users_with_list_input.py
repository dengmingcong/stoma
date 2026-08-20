"""Creates list of users with given input array.。

Generated from OpenAPI: createUsersWithListInput
Creates list of users with given input array.
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import CreateUsersWithListInputRequest, User
from ..router import router


@router.post("/user/createWithList")
class CreateUsersWithListInput(APIRoute[User]):
    """Creates list of users with given input array.。

    Creates list of users with given input array.
    """

    body: CreateUsersWithListInputRequest
