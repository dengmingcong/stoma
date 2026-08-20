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
from stoma import APIRoute, APIRouter

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

router = APIRouter(prefix="/v2")

@router.get("/user/{username}")
class GetUserByName(APIRoute[User]):
    """Get user by user name.。

    Get user detail based on username.
    """

    username: str
    """The name that needs to be fetched. Use user1 for testing"""

```

* `router = APIRouter(prefix="/v2")` - 实例化 `APIRouter`，并为所有关联接口设置公共的路径前缀 `/v2`。
* `@router.get("/user/{username}")` - 定义接口的请求方法（`GET`）和路径（`/user/{username}`），其中包含一个路径参数 `username`。
* `class GetUserByName(APIRoute[User]):` - 定义接口，Stoma 中一个接口必须是 `APIRoute` 子类。
    - `APIRoute` 是 pydantic `BaseModel` 子类，定义接口和定义 pydantic 模型是相同的书写方式。
    - `APIRoute` 同时也是泛型，泛型参数是接口的响应类型。当接口响应 Header `Content-Type` 是 JSON（如 `application/json`）时，会使用泛型参数的值去校验响应体并返回对应实例，示例会返回 `User` 实例。
* `username: str` - Path 参数。如果字段名和路径参数相同，会被识别为 Path 参数。


## 调用接口


```python
from playwright.sync_api import sync_playwright
from stoma import Client

with sync_playwright() as p:
    ctx = pw.request.new_context(base_url="http://localhost:8000")
    client = Client(context=ctx)

    # GET /users
    get_response = client.send(GetUsers(limit=10))
    print(get_response.raw.status)
    print(get_response.validated)

    # POST /users
    post_response = client.send(CreateUser(name="alice", email="alice@example.com"))
    print(post_response.raw.status)
    print(post_response.validated)
```

`Client.send` 返回一个 `Response[T]` 对象：
- `raw` 是 Playwright 原生 `APIResponse`，可取 status、headers 等。
- `validated` 是泛型参数 `T` 解析后的响应体，类型由 stoma 根据路由类的泛型自动推断。

## 4. 用 pytest 包起来

把上面的请求逻辑收进一个最小化的 pytest 测试函数：

```python
import pytest
from playwright.sync_api import sync_playwright as pw
from stoma import Client


@pytest.fixture
def client():
    with pw() as p:
        ctx = pw.request.new_context(base_url="http://localhost:8000")
        yield Client(context=ctx)
        ctx.dispose()


def test_get_users(client):
    response = client.send(GetUsers(limit=10))
    assert response.raw.status == 200
    assert isinstance(response.validated, list)


def test_create_user(client):
    response = client.send(CreateUser(name="bob", email="bob@example.com"))
    assert response.raw.status == 200
    assert response.validated["name"] == "bob"
```

`client` 是 pytest fixture，在每个测试结束后自动清理 Playwright context。

---

以上涵盖了从安装到写出第一个可运行测试的全流程。stoma 的核心用法可以归结为三步：

1. 用 `APIRoute` 定义接口，声明参数和响应类型。
2. 用 `APIRouter` 组织路由，提供 get/post 等装饰器。
3. 用 `Client` 发送请求，`Response[T]` 拿到带类型的响应体。

继续阅读下一份文档，了解路由的完整用法：

[继续：路由详解](./defining-routes.md)
