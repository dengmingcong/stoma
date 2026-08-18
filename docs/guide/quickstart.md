# 快速开始

10 分钟跑通一个端到端的接口测试流程。

## 1. 安装

建议使用 Python 3.11：

```bash
python3 --version
```

stoma 将接口定义和 Playwright（Python 版）作为核心依赖，并通过 extras 提供可选的功能扩展。

```bash
# 核心（pydantic + playwright 运行时；可 import stoma + 用 Client）
pip install stoma

# 加 CLI 工具 stoma make
pip install stoma[cli]

# 加测试基础设施（pytest + FastAPI mock server）
pip install stoma[test]

# 开发（全部 + 类型/lint）
pip install stoma[dev]
```

推荐同时安装 CLI 和测试工具：

```bash
pip install stoma[cli,test]
```

## 2. 第一个 endpoint

用一个最简的 users-CRUD（获取用户列表、创建用户）来演示 stoma 的声明式风格。

首先定义两个 APIRoute（GET + POST），全部从 stoma 公开 API 引入：

```python
from stoma import APIRoute, APIRouter, Query, Client

router = APIRouter()


@router.get("/users")
class GetUsers(APIRoute[list[dict]]):
    """获取用户列表。"""

    limit: int = 20


@router.post("/users")
class CreateUser(APIRoute[dict]):
    """创建用户。"""

    name: str
    email: str
```

stoma 的路由类继承自 `APIRoute`，泛型参数 `T` 指定响应体的类型（这里用 `dict` 简化演示）。类属性直接对应接口参数：`limit` 作为查询参数，`name` 和 `email` 作为请求体。

## 3. 发送请求

准备好一个运行中的 API 服务（假设在 `http://localhost:8000`），然后用 Playwright 的 `request.new_context` 建 context，再交给 Client 发送：

```python
from playwright.sync_api import sync_playwright as pw
from stoma import Client

with pw() as p:
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
