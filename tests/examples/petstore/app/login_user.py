"""Logs user into the system.。

Generated from OpenAPI: loginUser
Log into the system.
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

router = APIRouter()


@router.get("/user/login")
class LoginUser(APIRoute):
    """Logs user into the system.。

    Log into the system.
    """

    username: str | None = None
    """The user name for login"""
    password: str | None = None
    """The password for login in clear text"""
