from typing import Optional, Type

from openapi_pydantic import (
    DataType,
    MediaType,
    Operation,
    PathItem,
    Response,
    Schema,
    Server,
)
from playwright.sync_api import APIRequestContext
from pydantic import BaseModel

GET_USERS = PathItem(
    servers=[Server(url="https://jsonplaceholder.typicode.com")],
    get=Operation(
        responses={
            "200": Response(
                description="Successful response",
                content={
                    "application/json": MediaType(
                        schema=Schema(
                            type=DataType.OBJECT,
                            properties={
                                "id": Schema(type=DataType.INTEGER),
                                "name": Schema(type=DataType.STRING),
                                "username": Schema(type=DataType.STRING),
                                "email": Schema(type=DataType.STRING),
                                "address": Schema(
                                    type=DataType.OBJECT,
                                    properties={
                                        "street": Schema(type=DataType.STRING),
                                        "suite": Schema(type=DataType.STRING),
                                        "city": Schema(type=DataType.STRING),
                                        "zipcode": Schema(type=DataType.STRING),
                                        "geo": Schema(
                                            type=DataType.OBJECT,
                                            properties={
                                                "lat": Schema(type=DataType.STRING),
                                                "lng": Schema(type=DataType.STRING),
                                            },
                                        ),
                                    },
                                ),
                                "phone": Schema(type=DataType.STRING),
                                "website": Schema(type=DataType.STRING),
                                "company": Schema(
                                    type=DataType.OBJECT,
                                    properties={
                                        "name": Schema(type=DataType.STRING),
                                        "catchPhrase": Schema(type=DataType.STRING),
                                        "bs": Schema(type=DataType.STRING),
                                    },
                                ),
                            },
                        )
                    )
                },
            )
        },
    ),
)


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


class GetUsersRequestSchema(BaseModel):
    pass


class GetUsersResponseSchema(BaseModel):
    payload: list[User]


class GetUsers:
    def __init__(self, api_request_context: APIRequestContext):
        self.request: RequestSpec = RequestSpec(
            url="https://jsonplaceholder.typicode.com/users",
            method="GET",
            headers={},
            schema=GetUsersRequestSchema,
        )
        self.response: ResponseSpec = ResponseSpec(
            headers={
                "Content-Type": "application/json; charset=utf-8",
            },
            schema=GetUsersResponseSchema,
        )
        self.api_request_context: APIRequestContext = api_request_context

    def call(self) -> ResponseSpec:
        response = self.api_request_context.get(self.request.origin + self.request.path)
        return ResponseSpec(**response.json())
