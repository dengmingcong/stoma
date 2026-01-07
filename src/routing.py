"""路由相关的核心类型和装饰器。

此模块提供了类似 FastAPI 风格的路由定义能力，包括：

- RouteMeta：不可变的路由元数据类。
- APIRoute：接口基类。
- api_route_decorator：类装饰器工厂函数。
- APIRouter：路由装饰器提供者（待实现）。
"""

from collections.abc import Callable
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict


class RouteMeta(BaseModel):
    """路由元数据，不可变。

    用于存储接口的 HTTP 方法、路径信息和服务器列表，通过装饰器注入到接口类中。

    :var method: HTTP 方法（GET、POST、PUT、PATCH、DELETE 等）。
    :vartype method: str
    :var path: 接口路径，支持路径参数占位符（如 /users/{user_id}）。
    :vartype path: str
    :var servers: 接口级别的服务器列表，优先级高于 APIRouter 的全局 servers。
    :vartype servers: list[str] | None

    Example::

        meta = RouteMeta(method="GET", path="/users/{user_id}")
        print(meta.method)  # GET
        print(meta.path)    # /users/{user_id}
        print(meta.servers) # None 或 ["https://api.example.com"]
    """

    model_config = ConfigDict(frozen=True)

    method: str
    path: str
    servers: list[str] | None = None


class APIRoute[T](BaseModel):
    """接口基类，通过泛型指定响应模型类型。

    设计特点：

    1. 继承 BaseModel：自动 __init__ 生成，参数 → 属性，无需样板代码。
    2. 元数据隔离：所有路由信息存储在 _route_meta，避免与用户字段冲突。
    3. IDE 支持：字段声明即完成一切，IDE 完美补全与类型检查。

    :var _route_meta: 路由元数据，通过装饰器在类定义时注入。
    :vartype _route_meta: ClassVar[RouteMeta]

    Example::

        @router.get(path="/users")
        class GetUsers(APIRoute[list[UserData]]):
            limit: Annotated[int, Query(ge=1, le=100)] = 20

        endpoint = GetUsers(limit=10)
        users = endpoint()  # 返回 list[UserData]
    """

    _route_meta: ClassVar[RouteMeta]

    def __call__(self) -> T:
        """通用 __call__ 方法（由框架基类实现）。

        功能：

        1. 从实例字段自动收集请求参数（query/path/header/body）。
        2. 使用 Playwright 发送 HTTP 请求。
        3. 将响应 JSON 自动解析为泛型类型 T 的实例。

        详细实现将在用户故事 2 中完成。

        .. note::
            当前版本为同步实现，异步支持将在后续版本添加。

        :return: 响应数据，类型为泛型参数 T。
        :rtype: T
        :raise NotImplementedError: 当前占位符实现，实际功能待用户故事 2 完成。
        """
        msg = "__call__ 方法尚未实现，将在用户故事 2 中完成"
        raise NotImplementedError(msg)


def api_route_decorator[T: APIRoute[Any]](
    *,
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
    path: str,
    servers: list[str] | None = None,
) -> Callable[[type[T]], type[T]]:
    """类装饰器工厂函数，用于注入路由元数据到接口类。

    在类定义处通过装饰器语法传入 HTTP 方法、路径和服务器列表。
    被装饰的类必须继承自 APIRoute。

    :param method: HTTP 方法，必须是 GET、POST、PUT、PATCH、DELETE 之一。
    :type method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    :param path: 接口路径，支持路径参数占位符（如 /users/{user_id}）。
    :type path: str
    :param servers: 接口级别的服务器列表，优先级高于 APIRouter 的全局 servers。
    :type servers: list[str] | None
    :return: 类装饰器函数，接收并返回 APIRoute 子类。
    :rtype: Callable[[type[T]], type[T]]

    Example::

        @api_route_decorator(method="GET", path="/users/{user_id}")
        class GetUserById(APIRoute[UserData]):
            user_id: Annotated[int, Path()]

        # 验证元数据已注入
        assert GetUserById._route_meta.method == "GET"
        assert GetUserById._route_meta.path == "/users/{user_id}"
    """

    def update_api_route(cls: type[T]) -> type[T]:
        """内部装饰器函数，将路由元数据注入到类中。

        :param cls: 要装饰的 APIRoute 子类。
        :type cls: type[T]
        :return: 注入元数据后的类（原地修改，无新类生成）。
        :rtype: type[T]
        """
        cls._route_meta = RouteMeta(
            method=method,
            path=path,
            servers=servers,
        )
        return cls

    return update_api_route
