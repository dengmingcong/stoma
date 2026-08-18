"""Mock form login。

Generated from OpenAPI: post-login
Accepts an application/x-www-form-urlencoded username and password and returns a mock bearer token.
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute
from .models import TokenResponseBody, ErrorModel

router = APIRouter()


@router.post("/login")
class PostLogin(APIRoute[TokenResponseBody | ErrorModel]):
    """Mock form login。

    Accepts an application/x-www-form-urlencoded username and password and returns a mock bearer token.
    """
