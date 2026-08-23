from typing import Annotated

from playwright.sync_api import sync_playwright
from pydantic import BaseModel, Field

from stoma import APIRoute, APIRouter, Client, ResponseSpec


class User(BaseModel):
    id: Annotated[int | None, Field(examples=[10])] = None
    """Example: 10"""
    username: Annotated[str | None, Field(examples=["theUser"])] = None
    """Example: 'theUser'"""
    first_name: Annotated[str | None, Field(alias="firstName", examples=["John"])] = None
    """Example: 'John'"""
    last_name: Annotated[str | None, Field(alias="lastName", examples=["James"])] = None
    """Example: 'James'"""
    email: Annotated[str | None, Field(examples=["john@email.com"])] = None
    """Example: 'john@email.com'"""
    password: Annotated[str | None, Field(examples=["12345"])] = None
    """Example: '12345'"""
    phone: Annotated[str | None, Field(examples=["12345"])] = None
    """Example: '12345'"""
    user_status: Annotated[int | None, Field(alias="userStatus", examples=[1])] = None
    """
    User Status

    Example: 1
    """


router = APIRouter(prefix="/api/v3")


@router.get("/user/{username}")
class GetUserByName(APIRoute):
    """Get user by user name.。

    Get user detail based on username.
    """

    username: str
    """The name that needs to be fetched. Use user1 for testing"""

    @property
    def on_200(self) -> ResponseSpec[User]:
        return ResponseSpec(
            status_code=200,
            media_type="application/json",
            expected_type=User,
        )


with sync_playwright() as p:
    ctx = p.request.new_context(base_url="https://petstore3.swagger.io")
    client = Client(context=ctx)

    endpoint = GetUserByName(username="user1")
    response = client.send(endpoint)
    user = response.expect(endpoint.on_200)
    assert user.username == "user1"
