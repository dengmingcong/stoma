"""路由相关的核心类型和装饰器。

此模块提供了类似 FastAPI 风格的路由定义能力，包括：

- APIRoute：接口基类。
- api_route_decorator：类装饰器工厂函数。
- APIRouter：路由装饰器提供者。
"""

import re
from collections.abc import Callable
from typing import Annotated, Any, ClassVar, Literal, get_args, get_origin

from playwright.sync_api import APIRequestContext
from pydantic import BaseModel, TypeAdapter
from pydantic.fields import FieldInfo

from src.dependencies import Dependant, ModelField
from src.exceptions import HTTPError, ParseError, ValidationError
from src.params import Param, ParamTypes


class APIRoute[T](BaseModel):
    """接口基类，通过泛型指定响应模型类型。

    设计特点：

    1. 继承 BaseModel：自动 __init__ 生成，参数 → 属性，无需样板代码。
    2. 元数据缓存：所有路由信息和参数依赖存储在 _dependant，避免与用户字段冲突。
    3. IDE 支持：字段声明即完成一切，IDE 完美补全与类型检查。
    4. 懒加载优化：参数依赖分析结果缓存在类级别，提升性能。

    :var _dependant: 路由元数据和参数依赖定义缓存。
    :vartype _dependant: ClassVar[Dependant | None]

    Example::

        @router.get(path="/users")
        class GetUsers(APIRoute[list[UserData]]):
            limit: Annotated[int, Query(ge=1, le=100)] = 20

        endpoint = GetUsers(limit=10)
        users = endpoint.send(context)  # 返回 list[UserData]
    """

    _dependant: ClassVar[Dependant | None] = None

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
                model_field = ModelField(
                    name=field_name,
                    field_info=field_info,
                )

                # 1. 检查是否有显式的 Param 标记
                param_info = cls._get_param_info_from_field(field_name, field_info)

                if param_info is not None:
                    # 如果有显式标记，直接使用标记的类型
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
                        response_type = args[0]
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
    def _get_param_info_from_field(cls, field_name: str, field_info: FieldInfo) -> Param | None:
        """从字段中提取显式的 Param 标记信息。

        从类的 __annotations__ 中检查 Annotated 类型，提取 Param 对象。

        注意：FieldInfo.metadata 不会保存 Param 对象（已被 Pydantic 消费并转换为约束），
        因此必须从原始类型注解 __annotations__ 中获取。

        :param field_name: 字段名称。
        :type field_name: str
        :param field_info: Pydantic 字段信息对象（未使用，保留用于接口一致性）。
        :type field_info: FieldInfo
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

    def _interpolate_path_params(self) -> str:
        """插值路径参数（将路径中的 {param} 占位符替换为实际值）。

        根据 Dependant 中的路径参数定义，从实例中获取参数值，
        替换路径字符串中的 `{param}` 占位符。

        例如：
        - 原始路径: "/users/{user_id}/posts/{post_id}"
        - 参数: user_id=123, post_id=456
        - 结果: "/users/123/posts/456"

        :return: 插值后的路径字符串。
        :rtype: str
        """
        dependant = self._get_dependant()
        interpolated_path = dependant.path

        # 遍历路径参数，将占位符替换为实际值
        for model_field in dependant.path_params:
            # 获取参数值
            param_value = getattr(self, model_field.name)
            # 使用字段名（而非别名）替换占位符
            placeholder = f"{{{model_field.name}}}"
            interpolated_path = interpolated_path.replace(placeholder, str(param_value))

        return interpolated_path

    def _serialize_query_params(self) -> dict[str, str]:
        """序列化查询参数为字典（用于 URL query string）。

        从 Dependant 中的查询参数定义获取参数列表，
        从实例中提取参数值，转换为字典形式。

        查询参数的值转换规则：
        - None 值：跳过（不包含在结果中）
        - 布尔值：转换为 'true'/'false'
        - 列表/数组：重复的键值对
        - 其他：转换为字符串

        例如：
        - 输入参数: limit=20, offset=0, keyword=None
        - 结果: {'limit': '20', 'offset': '0'} (keyword 被过滤)

        :return: 查询参数字典（key → str value）。
        :rtype: dict[str, str]
        """
        dependant = self._get_dependant()
        query_params: dict[str, str] = {}

        # 遍历查询参数
        for model_field in dependant.query_params:
            # 获取参数值
            param_value = getattr(self, model_field.name)

            # 跳过 None 值
            if param_value is None:
                continue

            # 处理布尔值
            if isinstance(param_value, bool):
                param_value = "true" if param_value else "false"
            else:
                param_value = str(param_value)

            # 使用别名作为 query string 中的键
            query_params[model_field.alias] = param_value

        return query_params

    def _serialize_body_params(self) -> str | None:
        """序列化请求体参数为 JSON 字符串。

        从 Dependant 中的请求体参数定义获取参数列表，
        从实例中提取参数值，转换为 JSON 字符串。

        支持多种请求体格式：
        - 单个 BaseModel 实例：直接序列化为 JSON
        - 多个参数：合并为字典后序列化为 JSON
        - 无请求体：返回 None

        :return: JSON 字符串，如果无请求体则返回 None。
        :rtype: str | None
        """
        dependant = self._get_dependant()

        if not dependant.body_params:
            return None

        # 收集请求体数据
        body_data: dict[str, Any] = {}

        for model_field in dependant.body_params:
            param_value = getattr(self, model_field.name)

            # 跳过 None 值
            if param_value is None:
                continue

            # 如果是 Pydantic BaseModel 实例，展开其字段
            if isinstance(param_value, BaseModel):
                # 使用 model_dump 获取字典（排除 None 值）
                body_data.update(param_value.model_dump(exclude_none=True))
            else:
                body_data[model_field.alias] = param_value

        # 如果没有数据，返回 None
        if not body_data:
            return None

        # 序列化为 JSON 字符串
        import json

        return json.dumps(body_data, ensure_ascii=False)

    def _serialize_header_params(self) -> dict[str, str]:
        """序列化请求头参数为字典。

        从 Dependant 中的请求头参数定义获取参数列表，
        从实例中提取参数值，转换为字典形式。
        应用别名转换（snake_case → kebab-case）。

        :return: 请求头参数字典（key → str value）。
        :rtype: dict[str, str]
        """
        dependant = self._get_dependant()
        header_params: dict[str, str] = {}

        # 遍历请求头参数
        for model_field in dependant.header_params:
            # 获取参数值
            param_value = getattr(self, model_field.name)

            # 跳过 None 值
            if param_value is None:
                continue

            # 处理布尔值
            if isinstance(param_value, bool):
                param_value = "true" if param_value else "false"
            else:
                param_value = str(param_value)

            # 应用别名转换：如果字段名是 snake_case，转换为 kebab-case
            # 如果已有别名（来自 Header(...)），使用别名
            alias = model_field.alias

            # 如果别名与字段名不同（说明是通过 Annotated[Type, Header(...)] 设置的）
            # 直接使用别名；否则将 snake_case 转换为 kebab-case
            if alias == model_field.name:
                # 将 snake_case 转换为 kebab-case
                alias = alias.replace("_", "-")

            header_params[alias] = param_value

        return header_params

    def _build_url(self, servers: list[str] | None = None) -> str:
        """构建完整的请求 URL。

        基于 servers 配置、路径参数插值和查询参数拼接构建完整 URL。

        :param servers: 服务器地址列表，如果为 None 则使用全局配置。
        :type servers: list[str] | None
        :return: 完整的请求 URL。
        :rtype: str
        """
        # 1. 确定 base URL
        base_url = ""
        if servers:
            base_url = servers[0]
        elif hasattr(self, "_servers") and self._servers:
            base_url = self._servers[0]

        # 确保 base_url 有协议前缀（默认使用 http）
        if base_url and not base_url.startswith(("http://", "https://")):
            base_url = f"http://{base_url}"

        # 2. 插值路径参数
        interpolated_path = self._interpolate_path_params()

        # 3. 序列化查询参数
        query_dict = self._serialize_query_params()

        # 4. 构建完整 URL
        url = base_url + interpolated_path

        if query_dict:
            # 将查询参数字典转换为 query string
            query_parts = [f"{k}={v}" for k, v in query_dict.items()]
            url = url + "?" + "&".join(query_parts)

        return url

    def _send_request(self, context: APIRequestContext) -> Any:
        """使用 Playwright 发送 HTTP 请求并获取原始响应。

        :param context: Playwright 的 APIRequestContext 实例。
        :type context: APIRequestContext
        :return: Playwright 响应对象。
        :rtype: Any
        :raise HTTPError: 当请求失败、超时或服务器返回错误状态码。
        """
        dependant = self._get_dependant()

        # 获取 servers 配置
        servers: list[str] | None = getattr(self, "_servers", None)

        # 构建 URL
        url = self._build_url(servers=servers)

        # 准备请求头
        headers = self._serialize_header_params()

        # 准备请求体
        body = self._serialize_body_params()

        # 方法映射
        method_map = {
            "GET": context.get,
            "POST": context.post,
            "PUT": context.put,
            "PATCH": context.patch,
            "DELETE": context.delete,
        }

        request_method = method_map.get(dependant.method)
        if request_method is None:
            msg = f"不支持的 HTTP 方法: {dependant.method}"
            raise HTTPError(msg)

        try:
            # 发送请求
            response = request_method(
                url,
                headers=headers if headers else None,
                data=body,
            )
            return response
        except Exception as e:
            msg = f"HTTP 请求失败: {e}"
            raise HTTPError(msg) from e

    def _parse_response(self, response: Any) -> T:
        """解析 HTTP 响应并验证数据类型。

        将 Playwright 响应解析为泛型类型 T 的实例。

        :param response: Playwright 响应对象。
        :type response: Any
        :return: 类型为泛型参数 T 的响应数据。
        :rtype: T
        :raise HTTPError: 当 HTTP 状态码表示错误。
        :raise ParseError: 当响应无法解析为 JSON。
        :raise ValidationError: 当 JSON 数据无法通过 Pydantic 模型验证。
        """
        # 检查 HTTP 状态码
        if response.status >= 400:
            msg = f"HTTP 错误: 状态码 {response.status}"
            raise HTTPError(
                msg,
                status_code=response.status,
                response_text=response.text if hasattr(response, "text") else None,
            )

        # 获取响应类型（由 _get_dependant 缓存）
        dependant = self._get_dependant()

        # 如果响应类型是 NoneType，直接返回
        if dependant.response_type is type(None):
            return None  # type: ignore

        # 解析 JSON
        try:
            response_data = response.json()
        except Exception as e:
            msg = f"响应 JSON 解析失败: {e}"
            raise ParseError(msg, response_text=response.text) from e

        # 使用缓存的 TypeAdapter 验证响应数据
        assert dependant.response_type_adapter is not None
        try:
            return dependant.response_type_adapter.validate_python(response_data)  # type: ignore[no-any-return]
        except Exception as e:
            msg = f"响应数据验证失败: {e}"
            errors: list[dict[str, Any]] = []
            if hasattr(e, "errors"):
                errors = list(e.errors())
            raise ValidationError(msg, errors=errors) from e

    def send(self, context: APIRequestContext) -> T:
        """发送 HTTP 请求并返回响应数据。

        功能：

        1. 从实例字段自动收集请求参数（query/path/header/body）。
        2. 使用传入的 APIRequestContext 发送 HTTP 请求。
        3. 将响应 JSON 自动解析为泛型类型 T 的实例。

        :param context: Playwright 的 APIRequestContext 实例，用于发送 HTTP 请求。
        :type context: APIRequestContext
        :return: 响应数据，类型为泛型参数 T。
        :rtype: T
        :raise HTTPError: 当请求失败、超时或服务器返回错误状态码。
        :raise ParseError: 当响应无法解析为 JSON。
        :raise ValidationError: 当响应数据无法通过 Pydantic 模型验证。
        """
        try:
            # 1. 发送请求
            response = self._send_request(context)

            # 2. 解析响应
            return self._parse_response(response)
        except HTTPError:
            # HTTPError 已经包含足够的信息，直接重新抛出
            raise
        except ParseError:
            raise
        except ValidationError:
            raise
        except Exception as e:
            # 包装其他异常
            msg = f"请求发送失败: {e}"
            raise HTTPError(msg) from e


def api_route_decorator[T: APIRoute[Any]](
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

    def get[T: APIRoute[Any]](self, path: str) -> Callable[[type[T]], type[T]]:
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

    def post[T: APIRoute[Any]](self, path: str) -> Callable[[type[T]], type[T]]:
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

    def put[T: APIRoute[Any]](self, path: str) -> Callable[[type[T]], type[T]]:
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

    def patch[T: APIRoute[Any]](self, path: str) -> Callable[[type[T]], type[T]]:
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

    def delete[T: APIRoute[Any]](self, path: str) -> Callable[[type[T]], type[T]]:
        """DELETE 请求装饰器。

        :param path: 接口路径，支持路径参数占位符（如 /users/{user_id}）。
        :type path: str
        :return: 类装饰器函数。
        :rtype: Callable[[type[T]], type[T]]

        Example::

            @router.delete("/users/{user_id}")
            class DeleteUser(APIRoute[None]):
                user_id: Annotated[int, Path()]
        """
        return api_route_decorator(method="DELETE", path=path)
