"""路由相关的核心类型和装饰器。

此模块提供了类似 FastAPI 风格的路由定义能力，包括：

- RouteMeta：不可变的路由元数据类。
- APIRoute：接口基类。
- api_route_decorator：类装饰器工厂函数。
- APIRouter：路由装饰器提供者，支持全局和接口级 servers 配置。
"""

import re
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
    4. 参数识别缓存：参数类型识别结果缓存在 _param_mapping，提升性能。
    5. 别名缓存：参数名称别名映射缓存在 _param_aliases，避免重复查询。

    :var _route_meta: 路由元数据，通过装饰器在类定义时注入。
    :vartype _route_meta: ClassVar[RouteMeta]
    :var _param_mapping: 参数类型映射缓存，键为字段名，值为 ParamTypes。
    :vartype _param_mapping: ClassVar[dict[str, ParamTypes] | None]
    :var _param_aliases: 参数别名映射缓存，键为字段名，值为别名或字段名本身。
    :vartype _param_aliases: ClassVar[dict[str, str] | None]

    Example::

        @router.get(path="/users")
        class GetUsers(APIRoute[list[UserData]]):
            limit: Annotated[int, Query(ge=1, le=100)] = 20

        endpoint = GetUsers(limit=10)
        users = endpoint.send(context)  # 返回 list[UserData]
    """

    _route_meta: ClassVar[RouteMeta]
    _param_mapping: ClassVar[dict[str, ParamTypes] | None] = None
    _param_aliases: ClassVar[dict[str, str] | None] = None

    @classmethod
    def _build_param_mapping(cls) -> tuple[dict[str, ParamTypes], dict[str, str]]:
        """构建参数类型映射和别名映射缓存。

        根据规则自动识别每个字段的参数类型：

        - 路径参数（Path）：字段名出现在路由 path 中
        - 请求体（Body）：字段类型为 BaseModel 子类
        - 头参数（Header）：通过 Annotated[Type, Header(...)] 显式标记
        - 查询参数（Query）：默认类型（不满足上述条件）

        同时识别参数名称别名，用于 HTTP 请求中的实际参数名。

        识别结果缓存在类级别 _param_mapping 和 _param_aliases，后续调用直接复用。

        :return: 元组 (param_mapping, param_aliases)

            - param_mapping: 字段名 → 参数类型的映射字典
            - param_aliases: 字段名 → 实际参数名（别名或字段名本身）的映射字典

        :rtype: tuple[dict[str, ParamTypes], dict[str, str]]

        Example::

            @router.get("/users/{user_id}")
            class GetUser(APIRoute[UserData]):
                user_id: int
                page_size: Annotated[int, Query(alias="pageSize")] = 10
                token: Annotated[str, Header(alias="Authorization")]

            mapping, aliases = GetUser._build_param_mapping()
            # mapping = {
            #     "user_id": ParamTypes.path,
            #     "page_size": ParamTypes.query,
            #     "token": ParamTypes.header
            # }
            # aliases = {
            #     "user_id": "user_id",
            #     "page_size": "pageSize",
            #     "token": "Authorization"
            # }
        """
        param_mapping: dict[str, ParamTypes] = {}
        param_aliases: dict[str, str] = {}

        # 获取路径中的参数名（如 /users/{user_id} 中的 user_id）
        path_param_names = set()
        if hasattr(cls, "_route_meta"):
            path = cls._route_meta.path
            # 使用正则表达式提取路径参数 {param_name}
            path_param_names = set(re.findall(r"\{(\w+)\}", path))

        # 遍历所有字段，自动识别参数类型和别名
        for field_name, field_info in cls.model_fields.items():
            # 1. 检查是否有显式的 Param 标记（Header 必须显式标记）
            param_info = cls._get_param_info_from_field(field_name, field_info)
            if param_info is not None:
                # 如果有显式标记，直接使用标记的类型和别名
                param_mapping[field_name] = param_info.in_
                param_aliases[field_name] = param_info.alias if param_info.alias else field_name
                continue

            # 2. 检查是否是路径参数（字段名出现在路径中）
            if field_name in path_param_names:
                param_mapping[field_name] = ParamTypes.path
                param_aliases[field_name] = field_name
                continue

            # 3. 检查是否是请求体（类型为 BaseModel 子类）
            field_type = field_info.annotation
            # 处理 Annotated 类型，获取实际类型
            if get_origin(field_type) is Annotated:
                field_type = get_args(field_type)[0]

            # 检查是否是 BaseModel 子类（排除 BaseModel 本身）
            try:
                if isinstance(field_type, type) and issubclass(field_type, BaseModel) and field_type is not BaseModel:
                    param_mapping[field_name] = ParamTypes.body
                    param_aliases[field_name] = field_name
                    continue
            except TypeError:
                # 某些类型（如泛型）无法使用 issubclass 检查
                pass

            # 4. 默认为查询参数
            param_mapping[field_name] = ParamTypes.query
            param_aliases[field_name] = field_name

        return param_mapping, param_aliases

    @classmethod
    def _get_param_mapping(cls) -> dict[str, ParamTypes]:
        """获取参数类型映射缓存（懒加载）。

        首次调用时构建映射并缓存在类级别 _param_mapping，
        后续调用直接返回缓存结果。

        :return: 字段名 → 参数类型的映射字典。
        :rtype: dict[str, ParamTypes]
        """
        if cls._param_mapping is None:
            cls._param_mapping, cls._param_aliases = cls._build_param_mapping()
        return cls._param_mapping

    @classmethod
    def _get_param_aliases(cls) -> dict[str, str]:
        """获取参数别名映射缓存（懒加载）。

        首次调用时构建映射并缓存在类级别 _param_aliases，
        后续调用直接返回缓存结果。

        :return: 字段名 → 参数实际名称的映射字典。
        :rtype: dict[str, str]
        """
        if cls._param_aliases is None:
            cls._param_mapping, cls._param_aliases = cls._build_param_mapping()
        return cls._param_aliases

    @classmethod
    def _get_param_info_from_field(cls, field_name: str, field_info: FieldInfo) -> Param | None:
        """从字段中提取显式的 Param 标记信息。

        优先从类的 __annotations__ 中检查 Annotated 类型，
        然后检查 FieldInfo 的 metadata。

        :param field_name: 字段名称。
        :type field_name: str
        :param field_info: Pydantic 字段信息对象。
        :type field_info: FieldInfo
        :return: 参数标记对象，如果没有找到则返回 None。
        :rtype: Param | None
        """
        # 首先从 __annotations__ 中检查
        param_from_annotations = cls._get_param_info_from_annotations(field_name)
        if param_from_annotations is not None:
            return param_from_annotations

        # 然后从 FieldInfo 中检查
        return cls._get_param_info(field_info)

    @classmethod
    def _get_param_info_from_annotations(cls, field_name: str) -> Param | None:
        """从类的类型注解中提取参数标记信息。

        直接检查类的 __annotations__，从 Annotated 类型中提取 Param 对象。

        :param field_name: 字段名称。
        :type field_name: str
        :return: 参数标记对象，如果没有找到则返回 None。
        :rtype: Param | None
        """
        # 获取类的原始注解
        if not hasattr(cls, "__annotations__"):
            return None

        annotations = cls.__annotations__
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

    @staticmethod
    def _get_param_info(field_info: FieldInfo) -> Param | None:
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

    def _collect_params(
        self,
    ) -> dict[str, dict[str, Any] | Any]:
        """从实例字段收集请求参数。

        使用缓存的参数类型映射和别名映射，避免每次调用都重新识别。
        根据字段的参数类型，将字段值分类收集到对应的参数字典中。

        :return: 包含参数信息的字典，包含以下键：

            - "query": 查询参数字典，键为参数名（或别名），值为字段值
            - "path": 路径参数字典，键为参数名（或别名），值为字段值
            - "header": 请求头参数字典，键为参数名（或别名），值为字段值
            - "body": 请求体数据，可能是单个 Body 对象或 None

        :rtype: dict[str, dict[str, Any] | Any]

        Example::

            @router.get("/users/{user_id}")
            class GetUser(APIRoute[UserData]):
                user_id: int
                limit: int = 10
                token: Annotated[str, Header(alias="Authorization")]

            endpoint = GetUser(user_id=123, limit=20, token="Bearer xxx")
            params = endpoint._collect_params()
            # params = {
            #     "query": {"limit": 20},
            #     "path": {"user_id": 123},
            #     "header": {"Authorization": "Bearer xxx"},
            #     "body": None
            # }
        """
        query_params: dict[str, Any] = {}
        path_params: dict[str, Any] = {}
        header_params: dict[str, Any] = {}
        body_data: Any = None

        # 获取缓存的参数类型映射和别名映射
        param_mapping = self._get_param_mapping()
        param_aliases = self._get_param_aliases()

        # 遍历模型的所有字段
        for field_name in self.__class__.model_fields.keys():
            # 获取字段的实际值
            field_value = getattr(self, field_name)

            # 从缓存的映射中获取参数类型
            param_type = param_mapping.get(field_name)
            if param_type is None:
                # 如果没有映射信息，跳过该字段
                continue

            # 从缓存的别名映射中获取参数的实际名称
            param_name = param_aliases.get(field_name, field_name)

            # 根据参数类型分类收集
            if param_type == ParamTypes.query:
                query_params[param_name] = field_value
            elif param_type == ParamTypes.path:
                path_params[param_name] = field_value
            elif param_type == ParamTypes.header:
                header_params[param_name] = field_value
            elif param_type == ParamTypes.body:
                # Body 参数直接赋值（通常只有一个）
                body_data = field_value

        return {
            "query": query_params,
            "path": path_params,
            "header": header_params,
            "body": body_data,
        }

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
