# 定义路由

stoma 支持两种路由定义风格：装饰器风格和手动风格。两种风格在功能上完全等价，区别仅在于语法的直观程度和适用场景。

## 装饰器风格

通过 `APIRouter` 实例的 HTTP 方法装饰器（`get` / `post` / `patch` / `delete` 等）定义路由，是最常用的方式。以下以 users-CRUD 为例，覆盖 GET、POST、PATCH、DELETE 四个最小 endpoint：

```python
from typing import Annotated

from stoma import APIRoute, APIRouter, Query, Path

router = APIRouter()


@router.get("/users")
class GetUsers(APIRoute[list[dict]]):
    limit: int = 20


@router.get("/users/{user_id}")
class GetUserById(APIRoute[dict]):
    user_id: Annotated[int, Path()]


@router.post("/users")
class CreateUser(APIRoute[dict]):
    name: str
    email: str


@router.patch("/users/{user_id}")
class PatchUser(APIRoute[dict]):
    user_id: Annotated[int, Path()]
    email: str | None = None


@router.delete("/users/{user_id}")
class DeleteUser(APIRoute[dict]):
    user_id: Annotated[int, Path()]
```

每个装饰器接受 `path` 参数，路径中的 `{xxx}` 占位符与类中的 `Path()` 标记字段自动对应。装饰器风格保持了类定义与路由信息在同一行，符合直觉，适合日常开发。

## 手动风格（`api_route_decorator`）

通过 `api_route_decorator` 装饰器函数手动传入 HTTP 方法和路径，适用于方法或路径需要作为变量动态生成的场景：

```python
from typing import Annotated

from stoma import APIRoute, Path

# api_route_decorator 由 stoma.routing 内部模块提供，
# 此处展示其使用形态（import 路径不在 stoma 公开 API 中）：
# from stoma.routing import api_route_decorator


@api_route_decorator(method="GET", path="/users/{user_id}")
class GetUserByIdManual(APIRoute[dict]):
    user_id: Annotated[int, Path()]
```

在被装饰的类必须继承 `APIRoute` 的约束之外，手动风格与装饰器风格完全等价。两者的区别仅在于路由元数据的来源：装饰器风格通过 `router.get(path="/users")` 直接在装饰器参数中指定，手动风格通过 `api_route_decorator(method="GET", path="/users/{user_id}")` 传入。

选型指南：需要把方法加路径作为变量动态生成时选手动风格，日常开发选装饰器风格。

## HTTP 方法清单

`APIRouter` 提供了以下 8 个 HTTP 方法装饰器，对应 `src/stoma/routing.py:327-477` 的 docstring：

| 方法 | 签名 | 用途 |
|------|------|------|
| GET | `router.get(path)` | 获取资源，不改变服务器状态 |
| POST | `router.post(path)` | 创建新资源 |
| PUT | `router.put(path)` | 完整替换资源 |
| PATCH | `router.patch(path)` | 部分更新资源 |
| DELETE | `router.delete(path)` | 删除资源 |
| HEAD | `router.head(path)` | 与 GET 相同，但只返回响应头 |
| OPTIONS | `router.options(path)` | 返回服务器支持的 HTTP 方法 |
| TRACE | `router.trace(path)` | 回环测试，诊断请求路径 |

各方法的详细行为和参数说明参见 `APIRouter` 类的 docstring（`src/stoma/routing.py:327-477`）。

## 泛型参数 `T` 与响应类型

`APIRoute[T]` 的泛型参数 `T` 指定期望的 JSON 响应类型。例如 `APIRoute[list[dict]]` 表示响应体应当是 `list[dict]`。框架会利用 Pydantic `TypeAdapter` 对 JSON 响应体进行校验，并将校验结果存入 `response.validated`。

`T` 仅对 JSON 响应生效。如果接口返回非 JSON 响应（如纯文本或空 body），`T` 的类型校验不生效。参数标记的详细用法见下一文档。

## `_dependant` 的命名空间隔离

每个 `APIRoute` 子类在首次解析时，会通过 `_get_dependant` 方法生成并缓存路由元数据（`src/stoma/routing.py:53-55`）。元数据（HTTP 方法、路径、参数信息）存储在类变量 `_dependant` 中，与类的普通属性字段不在同一命名空间。

这意味着即使用户定义的字段名为 `method`、`path` 或 `servers`，也不会与路由元数据冲突。例如以下定义是合法的：

```python
from typing import Annotated

from stoma import APIRoute, APIRouter, Query

router = APIRouter()


@router.post("/debug")
class DebugEndpoint(APIRoute[dict]):
    method: Annotated[str, Query()]  # 不会与路由 method 元数据冲突
    path: Annotated[str, Query()]     # 不会与路由 path 元数据冲突
```

框架通过在 `_dependant` 类变量中独立存储元数据，实现了字段命名空间与路由元数据空间的隔离。

[继续：参数详解](./parameters.md)
