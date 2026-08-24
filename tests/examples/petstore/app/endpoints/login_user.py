"""Logs user into the system.。

Generated from OpenAPI: loginUser
Log into the system.
"""

from __future__ import annotations

from stoma import APIRoute, EmptyResponseSpec, ResponseSpec

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
    def on_200_application_xml(self) -> ResponseSpec[str]:
        return ResponseSpec(
            status_code=200,
            media_type="application/xml",
            expected_type=str,
        )

    @property
    def on_200_application_json(self) -> ResponseSpec[str]:
        return ResponseSpec(
            status_code=200,
            media_type="application/json",
            expected_type=str,
        )

    @property
    def on_400(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=400,
        )

    @property
    def on_default(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=lambda c: c not in [200, 400],
        )
