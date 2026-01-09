"""路由相关的核心类型和装饰器。

此模块提供了类似 FastAPI 风格的路由定义能力，包括：

- RouteMeta：不可变的路由元数据类。
- APIRoute：接口基类。
- api_route_decorator：类装饰器工厂函数。
- APIRouter：路由装饰器提供者，支持全局和接口级 servers 配置。
"""

from collections.abc import Callable
from typing import Annotated, Any, ClassVar, Literal, get_args, get_origin

from playwright.sync_api import APIRequestContext
from pydantic import BaseModel, ConfigDict
from pydantic.fields import FieldInfo

from src.params import Param, ParamTypes


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
        users = endpoint.send(context)  # 返回 list[UserData]
    """

    _route_meta: ClassVar[RouteMeta]

    def _collect_params(
        self,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], Any]:
        """从实例字段收集请求参数。

        遍历实例的所有字段，根据字段的 Annotated 元数据判断参数类型，
        将字段值分类收集到对应的参数字典中。

        :return: 四元组 (query_params, path_params, header_params, body_data)
            - query_params: 查询参数字典，键为参数名（或别名），值为字段值
            - path_params: 路径参数字典，键为参数名（或别名），值为字段值
            - header_params: 请求头参数字典，键为参数名（或别名），值为字段值
            - body_data: 请求体数据，可能是单个 Body 对象或 None
        :rtype: tuple[dict[str, Any], dict[str, Any], dict[str, Any], Any]

        Example::

            @router.get("/users/{user_id}")
            class GetUser(APIRoute[UserData]):
                user_id: Annotated[int, Path()]
                limit: Annotated[int, Query()] = 10
                token: Annotated[str, Header(alias="Authorization")]

            endpoint = GetUser(user_id=123, limit=20, token="Bearer xxx")
            query, path, headers, body = endpoint._collect_params()
            # query = {"limit": 20}
            # path = {"user_id": 123}
            # headers = {"Authorization": "Bearer xxx"}
            # body = None
        """
        query_params: dict[str, Any] = {}
        path_params: dict[str, Any] = {}
        header_params: dict[str, Any] = {}
        body_data: Any = None

        # 遍历模型的所有字段
        for field_name in self.__class__.model_fields.keys():
            # 获取字段的实际值
            field_value = getattr(self, field_name)

            # 从类的原始注解中获取参数信息
            param_info = self._get_param_info_from_annotations(field_name)

            if param_info is None:
                # 如果没有参数标记，跳过该字段
                continue

            # 获取参数的实际名称（使用别名或字段名）
            param_name = self._get_param_name(param_info, field_name)

            # 根据参数类型分类收集
            if param_info.in_ == ParamTypes.query:
                query_params[param_name] = field_value
            elif param_info.in_ == ParamTypes.path:
                path_params[param_name] = field_value
            elif param_info.in_ == ParamTypes.header:
                header_params[param_name] = field_value
            elif param_info.in_ == ParamTypes.body:
                # Body 参数直接赋值（通常只有一个）
                body_data = field_value

        return query_params, path_params, header_params, body_data

    def _get_param_info_from_annotations(self, field_name: str) -> Param | None:
        """从类的类型注解中提取参数标记信息。

        直接检查类的 __annotations__，从 Annotated 类型中提取 Param 对象。

        :param field_name: 字段名称。
        :type field_name: str
        :return: 参数标记对象，如果没有找到则返回 None。
        :rtype: Param | None
        """
        # 获取类的原始注解
        annotations = self.__class__.__annotations__
        if field_name not in annotations:
            return None

        # 获取字段的类型注解
        annotation = annotations[field_name]

        # 检查是否是 Annotated 类型
        origin = get_origin(annotation)
        if origin is not Annotated:
            return None

        # 获取 Annotated 的参数
        args = get_args(annotation)
        if len(args) < 2:
            return None

        # args[0] 是实际类型，args[1:] 是元数据
        for metadata in args[1:]:
            if isinstance(metadata, Param):
                return metadata

        return None

    def _get_param_info(self, field_info: FieldInfo) -> Param | None:
        """从字段的 FieldInfo 中提取参数标记信息。

        检查 FieldInfo 本身是否是 Param 类型的实例，或者检查其 metadata。

        :param field_info: Pydantic 字段信息对象。
        :type field_info: FieldInfo
        :return: 参数标记对象，如果没有找到则返回 None。
        :rtype: Param | None
        """
        # 首先检查 field_info 本身是否是 Param 的实例
        if isinstance(field_info, Param):
            return field_info

        # 然后检查 field_info 的 metadata 列表
        for metadata in field_info.metadata:
            if isinstance(metadata, Param):
                return metadata

        return None

    def _get_param_name(self, param_info: Param, field_name: str) -> str:
        """获取参数的实际名称，优先使用别名。

        :param param_info: 参数标记对象。
        :type param_info: Param
        :param field_name: 字段名称。
        :type field_name: str
        :return: 参数的实际名称（别名或字段名）。
        :rtype: str
        """
        # 如果有 alias，使用 alias
        if param_info.alias:
            return param_info.alias
        # 否则使用字段名
        return field_name

    def send(self, context: APIRequestContext) -> T:
        """发送 HTTP 请求并返回响应数据。

        功能：

        1. 从实例字段自动收集请求参数（query/path/header/body）。
        2. 使用传入的 APIRequestContext 发送 HTTP 请求。
        3. 将响应 JSON 自动解析为泛型类型 T 的实例。

        详细实现将在用户故事 2 中完成。

        .. note::
            当前版本为同步实现，异步支持将在后续版本添加。

        :param context: Playwright 的 APIRequestContext 实例，用于发送 HTTP 请求。
        :type context: APIRequestContext
        :return: 响应数据，类型为泛型参数 T。
        :rtype: T
        :raise NotImplementedError: 当前占位符实现，实际功能待用户故事 2 完成。
        """
        msg = "send 方法尚未实现，将在用户故事 2 中完成"
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


class APIRouter:
    """路由器，支持全局 servers 配置和接口级别的 servers 覆盖。

    提供类似 FastAPI 风格的路由装饰器方法（get/post/put/patch/delete），
    简化接口定义语法。支持全局 servers 配置和接口级别的 servers 覆盖。

    :var servers: 全局服务器列表，可被接口级 servers 参数覆盖。
    :vartype servers: list[str] | None

    Example::

        # 创建路由器并配置全局 servers
        router = APIRouter(servers=["https://api.example.com"])

        # 使用全局 servers
        @router.get("/users")
        class GetUsers(APIRoute[list[UserData]]):
            limit: int = 20

        # 覆盖全局 servers
        @router.post("/users", servers=["https://api-staging.example.com"])
        class CreateUser(APIRoute[UserData]):
            name: str
            email: str
    """

    def __init__(self, servers: list[str] | None = None) -> None:
        """初始化路由器，可指定全局服务器列表。

        :param servers: 全局服务器列表（如 OpenAPI servers），
            可在各个路由方法中通过 servers 参数覆盖。
        :type servers: list[str] | None
        """
        self.servers = servers

    def get[T: APIRoute[Any]](self, path: str, *, servers: list[str] | None = None) -> Callable[[type[T]], type[T]]:
        """GET 请求装饰器。

        :param path: 接口路径，支持路径参数占位符（如 /users/{user_id}）。
        :type path: str
        :param servers: 接口级服务器列表，如果提供则覆盖全局 servers。
        :type servers: list[str] | None
        :return: 类装饰器函数。
        :rtype: Callable[[type[T]], type[T]]

        Example::

            @router.get("/users")
            class GetUsers(APIRoute[list[UserData]]):
                limit: int = 20
        """
        return api_route_decorator(method="GET", path=path, servers=servers or self.servers)

    def post[T: APIRoute[Any]](self, path: str, *, servers: list[str] | None = None) -> Callable[[type[T]], type[T]]:
        """POST 请求装饰器。

        :param path: 接口路径，支持路径参数占位符（如 /users/{user_id}）。
        :type path: str
        :param servers: 接口级服务器列表，如果提供则覆盖全局 servers。
        :type servers: list[str] | None
        :return: 类装饰器函数。
        :rtype: Callable[[type[T]], type[T]]

        Example::

            @router.post("/users")
            class CreateUser(APIRoute[UserData]):
                name: str
                email: str
        """
        return api_route_decorator(method="POST", path=path, servers=servers or self.servers)

    def put[T: APIRoute[Any]](self, path: str, *, servers: list[str] | None = None) -> Callable[[type[T]], type[T]]:
        """PUT 请求装饰器。

        :param path: 接口路径，支持路径参数占位符（如 /users/{user_id}）。
        :type path: str
        :param servers: 接口级服务器列表，如果提供则覆盖全局 servers。
        :type servers: list[str] | None
        :return: 类装饰器函数。
        :rtype: Callable[[type[T]], type[T]]

        Example::

            @router.put("/users/{user_id}")
            class UpdateUser(APIRoute[UserData]):
                user_id: Annotated[int, Path()]
                name: str
        """
        return api_route_decorator(method="PUT", path=path, servers=servers or self.servers)

    def patch[T: APIRoute[Any]](self, path: str, *, servers: list[str] | None = None) -> Callable[[type[T]], type[T]]:
        """PATCH 请求装饰器。

        :param path: 接口路径，支持路径参数占位符（如 /users/{user_id}）。
        :type path: str
        :param servers: 接口级服务器列表，如果提供则覆盖全局 servers。
        :type servers: list[str] | None
        :return: 类装饰器函数。
        :rtype: Callable[[type[T]], type[T]]

        Example::

            @router.patch("/users/{user_id}")
            class PatchUser(APIRoute[UserData]):
                user_id: Annotated[int, Path()]
                email: str | None = None
        """
        return api_route_decorator(method="PATCH", path=path, servers=servers or self.servers)

    def delete[T: APIRoute[Any]](self, path: str, *, servers: list[str] | None = None) -> Callable[[type[T]], type[T]]:
        """DELETE 请求装饰器。

        :param path: 接口路径，支持路径参数占位符（如 /users/{user_id}）。
        :type path: str
        :param servers: 接口级服务器列表，如果提供则覆盖全局 servers。
        :type servers: list[str] | None
        :return: 类装饰器函数。
        :rtype: Callable[[type[T]], type[T]]

        Example::

            @router.delete("/users/{user_id}")
            class DeleteUser(APIRoute[None]):
                user_id: Annotated[int, Path()]
        """
        return api_route_decorator(method="DELETE", path=path, servers=servers or self.servers)
