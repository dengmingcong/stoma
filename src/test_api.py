from typing import Type

from playwright.sync_api import APIRequestContext
from pydantic import BaseModel


# 所有接口共用的请求/响应模型。
class Request(BaseModel):
    origin: str
    path: str
    method: str
    headers: dict[str, str]
    model: Type[BaseModel]


class Response(BaseModel):
    headers: dict[str, str]
    model: Type[BaseModel]


# 此接口独有的请求/响应模型和接口实现。
class User(BaseModel):
    id: int
    name: str
    username: str
    email: str
    phone: str
    website: str


class GetUsersRequest(BaseModel):
    pass


class GetUsersResponse(BaseModel):
    payload: list[User]


class GetUsers:
    def __init__(self, api_request_context: APIRequestContext):
        self.request: Request = Request(
            origin="https://jsonplaceholder.typicode.com",
            path="/users",
            method="GET",
            headers={},
            model=GetUsersRequest,
        )
        self.response: Response = Response(
            headers={
                "Content-Type": "application/json; charset=utf-8",
            },
            model=GetUsersResponse,
        )
        self.api_request_context: APIRequestContext = api_request_context

    def call(self) -> Response:
        response = self.api_request_context.get(self.request.origin + self.request.path)
        return Response(**response.json())
