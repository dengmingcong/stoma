"""路由相关的核心类型和装饰器。

此模块提供了类似 FastAPI 风格的路由定义能力，包括：

- APIRoute：接口基类（纯数据类：字段 + 路由元数据）。
- api_route_decorator：类装饰器工厂函数。
- APIRouter：路由装饰器提供者。

APIRoute 本身不持有 Playwright context，也不直接发送请求。
发送请求由 ``Client``（src/client.py）负责。
"""

import re
from collections.abc import Callable
from typing import Annotated, Any, ClassVar, Literal, get_args, get_origin

from pydantic import BaseModel, ConfigDict, TypeAdapter

from src.dependencies import Dependant, ModelField
from src.params import Param, ParamTypes


class APIRoute[T](BaseModel):
    """接口基类，纯数据类（字段 + 路由元数据）。

    通过泛型 ``T`` 指定响应模型类型。实际请求由 ``Client.send(api_route)`` 发起。

    :var _dependant: 路由元数据和参数依赖定义缓存。
    :vartype _dependant: ClassVar[Dependant | None]

    Example::

        @router.get(path="/users")
        class GetUsers(APIRoute[list[UserData]]):
            limit: Annotated[int, Query(ge=1, le=100)] = 20

        endpoint = GetUsers(limit=10)
        response = client.send(endpoint)  # 类型: Response[list[UserData]]
        if response.raw.status == 200:
            users = response.model  # 类型: list[UserData] | None
    """

    # Ref: https://pydantic.dev/docs/validation/latest/concepts/models/#class-variables
    _dependant: ClassVar[Dependant | None] = None
    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

    @classmethod
    def _get_dependant(
        cls,
        method: str | None = None,
        path: str | None = None,
    ) -> Dependant:
        """获取参数依赖定义缓存（懒加载）。

        首次调用时分析字段参数依赖并缓存在类级别 _dependant，
        后续调用直接返回缓存结果。

        根据规则自动识别每个字段的参数类型：
        - 路径参数（Path）：字段名出现在路由 path 中
        - 请求体（Body）：字段类型为 BaseModel 子类
        - 头参数（Header）：通过 Annotated[Type, Header(...)] 显式标记
        - 查询参数（Query）：默认类型（不满足上述条件）

        :param method: HTTP 方法，首次调用时必须提供。
        :type method: str | None
        :param path: 路由路径，首次调用时必须提供。
        :type path: str | None
        :return: 参数依赖定义对象。
        :rtype: Dependant
        """
        if cls._dependant is None:
            if method is None or path is None:
                msg = "首次调用 _get_dependant 必须提供 method 和 path 参数"
                raise ValueError(msg)

            path_params: list[ModelField] = []
            query_params: list[ModelField] = []
            header_params: list[ModelField] = []
            body_params: list[ModelField] = []

            # 使用正则表达式提取路径参数名
            path_param_names = set(re.findall(r"\{(\w+)\}", path))

            # 遍历所有字段，自动识别参数类型
            for field_name, field_info in cls.model_fields.items():
                # 从 __annotations__ 获取显式的 Param 标记
                param_info = cls._get_param_info_from_field(field_name)

                # 创建 ModelField，保留原始 field_info
                model_field = ModelField(name=field_name, field_info=field_info, param_info=param_info)

                if isinstance(param_info, Param):
                    if param_info.in_ == ParamTypes.path:
                        path_params.append(model_field)
                    elif param_info.in_ == ParamTypes.query:
                        query_params.append(model_field)
                    elif param_info.in_ == ParamTypes.header:
                        header_params.append(model_field)
                    elif param_info.in_ == ParamTypes.body:
                        body_params.append(model_field)
                    continue

                # 2. 检查是否是路径参数（字段名出现在路径中）
                if field_name in path_param_names:
                    path_params.append(model_field)
                    continue

                # 3. 检查是否是请求体（类型为 BaseModel 子类）
                # field_info.annotation 已经是 Pydantic 展开后的基础类型
                field_type = field_info.annotation

                # 检查是否是 BaseModel 子类（排除 BaseModel 本身）
                try:
                    if (
                        isinstance(field_type, type)
                        and issubclass(field_type, BaseModel)
                        and field_type is not BaseModel
                    ):
                        body_params.append(model_field)
                        continue
                except TypeError:
                    # 某些类型（如泛型）无法使用 issubclass 检查
                    pass

                # 4. 默认为查询参数
                query_params.append(model_field)

            # 提取响应类型
            response_type: type | None = None
            for c in cls.mro():
                name = c.__name__
                if name.startswith("APIRoute["):
                    metadata = getattr(c, "__pydantic_generic_metadata__", {})
                    if args := metadata.get("args"):
                        response_type = args[0]  # 如果泛型有多个参数，取第一个作为响应类型，忽略后续其他参数
                    break

            if response_type is None:
                msg = f"无法从 {cls.__name__} 获取响应类型，请确保继承自 APIRoute[ResponseType]"
                raise ValueError(msg)

            # 创建响应类型验证器
            response_type_adapter: TypeAdapter[Any] | None = None
            if response_type is not type(None):
                response_type_adapter = TypeAdapter(response_type)

            cls._dependant = Dependant(
                method=method,
                path=path,
                path_params=path_params,
                query_params=query_params,
                header_params=header_params,
                body_params=body_params,
                response_type=response_type,
                response_type_adapter=response_type_adapter,
            )

        return cls._dependant

    @classmethod
    def _get_param_info_from_field(cls, field_name: str) -> Param | None:
        """从字段中提取显式的 Param 标记信息。

        从类的 __annotations__ 中检查 Annotated 类型，提取 Param 对象。

        FastAPI 的处理方式：直接分析函数签名的 __annotations__，通过 get_origin()
        和 get_args() 从 Annotated 中提取 FieldInfo 子类（如 Body/Query/Path）。
        不依赖 model_fields，因为 Pydantic 会将 FieldInfo 子类的约束提取到普通 FieldInfo 中，
        而不保留原始的 Body/Query/Path 实例。

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


def api_route_decorator[T: APIRoute](
    *,
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
    path: str,
) -> Callable[[type[T]], type[T]]:
    """类装饰器工厂函数，用于注入路由元数据到接口类。

    在类定义处通过装饰器语法传入 HTTP 方法和路径。
    被装饰的类必须继承自 APIRoute。

    :param method: HTTP 方法，必须是 GET、POST、PUT、PATCH、DELETE 之一。
    :type method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    :param path: 接口路径，支持路径参数占位符（如 /users/{user_id}）。
    :type path: str
    :return: 类装饰器函数，接收并返回 APIRoute 子类。
    :rtype: Callable[[type[T]], type[T]]

    Example::

        @api_route_decorator(method="GET", path="/users/{user_id}")
        class GetUserById(APIRoute[UserData]):
            user_id: Annotated[int, Path()]

        # 验证元数据已注入
        dependant = GetUserById._get_dependant()
        assert dependant.method == "GET"
        assert dependant.path == "/users/{user_id}"
    """

    def update_api_route(cls: type[T]) -> type[T]:
        """内部装饰器函数，调用 _get_dependant 生成并缓存路由元数据。

        :param cls: 要装饰的 APIRoute 子类。
        :type cls: type[T]
        :return: 注入元数据后的类（原地修改，无新类生成）。
        :rtype: type[T]
        """
        # 调用 _get_dependant 生成并缓存元数据
        cls._get_dependant(method=method, path=path)
        return cls

    return update_api_route


class APIRouter:
    """路由器，提供便捷的路由装饰器方法。

    提供类似 FastAPI 风格的路由装饰器方法（get/post/put/patch/delete），
    简化接口定义语法。

    Example::

        # 创建路由器
        router = APIRouter()

        # 使用装饰器定义接口
        @router.get("/users")
        class GetUsers(APIRoute[list[UserData]]):
            limit: int = 20

        @router.post("/users")
        class CreateUser(APIRoute[UserData]):
            name: str
            email: str
    """

    def get[T: APIRoute](self, path: str) -> Callable[[type[T]], type[T]]:
        """GET 请求装饰器。

        :param path: 接口路径，支持路径参数占位符（如 /users/{user_id}）。
        :type path: str
        :return: 类装饰器函数。
        :rtype: Callable[[type[T]], type[T]]

        Example::

            @router.get("/users")
            class GetUsers(APIRoute[list[UserData]]):
                limit: int = 20
        """
        return api_route_decorator(method="GET", path=path)

    def post[T: APIRoute](self, path: str) -> Callable[[type[T]], type[T]]:
        """POST 请求装饰器。

        :param path: 接口路径，支持路径参数占位符（如 /users/{user_id}）。
        :type path: str
        :return: 类装饰器函数。
        :rtype: Callable[[type[T]], type[T]]

        Example::

            @router.post("/users")
            class CreateUser(APIRoute[UserData]):
                name: str
                email: str
        """
        return api_route_decorator(method="POST", path=path)

    def put[T: APIRoute](self, path: str) -> Callable[[type[T]], type[T]]:
        """PUT 请求装饰器。

        :param path: 接口路径，支持路径参数占位符（如 /users/{user_id}）。
        :type path: str
        :return: 类装饰器函数。
        :rtype: Callable[[type[T]], type[T]]

        Example::

            @router.put("/users/{user_id}")
            class UpdateUser(APIRoute[UserData]):
                user_id: Annotated[int, Path()]
                name: str
        """
        return api_route_decorator(method="PUT", path=path)

    def patch[T: APIRoute](self, path: str) -> Callable[[type[T]], type[T]]:
        """PATCH 请求装饰器。

        :param path: 接口路径，支持路径参数占位符（如 /users/{user_id}）。
        :type path: str
        :return: 类装饰器函数。
        :rtype: Callable[[type[T]], type[T]]

        Example::

            @router.patch("/users/{user_id}")
            class PatchUser(APIRoute[UserData]):
                user_id: Annotated[int, Path()]
                email: str | None = None
        """
        return api_route_decorator(method="PATCH", path=path)

    def delete[T: APIRoute](self, path: str) -> Callable[[type[T]], type[T]]:
        """DELETE 请求装饰器。

        :param path: 接口路径，支持路径参数占位符（如 /users/{user_id}）。
        :type path: str
        :return: 类装饰器函数。
        :rtype: Callable[[type[T]], type[T]]

        Example::

            @router.delete("/users/{user_id}")
            class DeleteUser(APIRoute[dict[str, str]]):
                user_id: Annotated[int, Path()]
        """
        return api_route_decorator(method="DELETE", path=path)
