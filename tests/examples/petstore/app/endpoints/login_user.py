"""Logs user into the system.。

Generated from OpenAPI: loginUser
Log into the system.
"""

from __future__ import annotations

from stoma import APIRoute, RawResponseSpec

from ..router import router


@router.get("/user/login")
class LoginUser(APIRoute):
    """Logs user into the system.。

    Log into the system.
    """

    username: str | None = None
    """The user name for login"""
    password: str | None = None
    """The password for login in clear text"""

    @property
    def on_200_application_xml(self) -> RawResponseSpec[str]:
        return RawResponseSpec(status_code=200, media_type="application/xml", target_type=str)
