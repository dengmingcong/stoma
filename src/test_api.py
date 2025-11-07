from typing import Optional, Type

from playwright.sync_api import APIRequestContext
from pydantic import BaseModel


# 所有接口共用的请求/响应模型。
class RequestSpec(BaseModel):
    url: str
    params: Optional[dict] = None
    method: str
    headers: dict[str, str] = {}
    schema: Type[BaseModel]


class ResponseSpec(BaseModel):
    headers: dict[str, str] = {}
    schema: Type[BaseModel]


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
        self.request: RequestSpec = RequestSpec(
            url="https://jsonplaceholder.typicode.com/users",
            method="GET",
            headers={},
            schema=GetUsersRequest,
        )
        self.response: ResponseSpec = ResponseSpec(
            headers={
                "Content-Type": "application/json; charset=utf-8",
            },
            schema=GetUsersResponse,
        )
        self.api_request_context: APIRequestContext = api_request_context

    def call(self) -> ResponseSpec:
        response = self.api_request_context.get(self.request.origin + self.request.path)
        return ResponseSpec(**response.json())
