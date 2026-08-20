"""Logs out current logged in user session.。

Generated from OpenAPI: logoutUser
Log user out of the system.
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

router = APIRouter()


@router.get("/user/logout")
class LogoutUser(APIRoute):
    """Logs out current logged in user session.。

    Log user out of the system.
    """
