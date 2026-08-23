# 快速开始


## 安装

需要使用 Python 3.12 及以上版本。

```bash
# 安装运行时需要的依赖
pip install stoma

# 安装运行时需要的依赖，并增加 CLI 需要的依赖
pip install stoma[cli]
```

## 定义接口

以 Swagger Petstore 接口 [getUserByName](https://petstore.swagger.io/#/user/getUserByName) 为例，说明 Stoma 中如何定义接口。

```python
from typing import Annotated
from pydantic import BaseModel, Field
from stoma import APIRoute, APIRouter, ResponseSpec

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
```

* `router = APIRouter(prefix="/api/v3")` - 实例化 `APIRouter`，并为所有关联接口设置公共的路径前缀 `/api/v3`。
* `@router.get("/user/{username}")` - 定义接口的请求方法（`GET`）和路径（`/user/{username}`），其中包含一个路径参数 `username`。最终接口路径为 `/api/v3/user/{username}`。
* `class GetUserByName(APIRoute):` - 定义接口，Stoma 中一个接口必须是 `APIRoute` 子类。同时 `APIRoute` 是 Pydantic `BaseModel` 子类，所以 Stoma 中定义接口和定义 Pydantic 模型是相同的书写方式。
    -  `username: str` - Path 参数。如果字段名和路径参数相同，会被识别为 Path 参数。
    - `property on_200` - 声明 Status Code 为 200 时的响应协议。

## 调用接口

```python
from playwright.sync_api import sync_playwright
from stoma import Client

with sync_playwright() as p:
    ctx = p.request.new_context(base_url="https://petstore3.swagger.io")
    client = Client(context=ctx)

    endpoint = GetUserByName(username="user1")
    response = client.send(endpoint)
    user = response.expect(endpoint.on_200)
    assert user.username == "user1"
```

* Stoma 内部使用 Playwright [APIRequestContext](https://playwright.dev/python/docs/api/class-apirequestcontext) 发送请求并管理 Cookie 等，Playwright 的所有特性均可以正常使用。
* Stoma 将所有接口定义为 Pydantic 模型，IDE 可以自动联想所有参数。
    ![alt text](../assets/guide/quickstart/ide-autocomplete-param.png)
    鼠标悬浮时还可查看参数的说明。
    ![alt text](../assets/guide/quickstart/hover-param.png)
* `Client.send()` 返回 `Response` 实例，`Response` 实例的 `expect()` 方法预期一个响应协议，会按照协议对 Status Code、Media type 校验，并使用 `pydantic.TypeAdapter` 将返回体转换为响应协议指定的模型，利用泛型特性实现 IDE 自动联想。
    ![alt text](../assets/guide/quickstart/ide-autocomplete-response.png)

## 回顾

以上涵盖了从安装到写出第一个可运行脚本的全流程。Stoma 的核心用法可以归结为三步：

1. 用 `APIRoute` 定义接口，声明参数和响应类型。
2. 用 `APIRouter` 组织路由。
3. 用 `Client` 发送请求。
