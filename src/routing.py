"""路由相关的核心类型和装饰器。

此模块提供了类似 FastAPI 风格的路由定义能力，包括：

- APIRoute：接口基类（纯数据类：字段 + 路由元数据）。
- api_route_decorator：类装饰器工厂函数。
- APIRouter：路由装饰器提供者。

APIRoute 本身不持有 Playwright context，也不直接发送请求。
发送请求由 ``Client``（src/client.py）负责。
"""

import pathlib
import re
from collections.abc import Callable
from types import UnionType  # Python 3.10+
from typing import Annotated, Any, ClassVar, Literal, Union, get_args, get_origin

from pydantic import BaseModel, ConfigDict, TypeAdapter

from src.dependencies import Dependant, ModelField
from src.dependencies.utils import _is_uploadfile_or_list_annotation, field_annotation_is_complex
from src.params import Form, Param, ParamTypes


def _is_path_or_list_annotation(annotation: Any) -> bool:
    """判断注解是否可识别为 pathlib.Path 类型的字段。

    支持以下形式（兼容 PEP 604 与 ``typing.Optional`` 写法）：

    - ``pathlib.Path``
    - ``list[pathlib.Path]``
    - ``pathlib.Path | None`` / ``Optional[pathlib.Path]``
    - ``list[pathlib.Path] | None`` / ``Optional[list[pathlib.Path]]``
    - 任意层 ``Union[pathlib.Path | None, list[pathlib.Path] | None]``（只要全部成员都是 Path 类型，则返回 True）

    实现要点：递归解包 ``Union`` / ``Optional``，跳过 ``None`` 成员，
    要求每个非 ``None`` 成员都是 ``pathlib.Path`` 或 ``list[pathlib.Path]``。

    :param annotation: 待检查的类型注解。
    :return: 如果是合法的 pathlib.Path 字段类型则返回 True。
    """
    origin = get_origin(annotation)
    if origin is Union or origin is UnionType:
        # ``Optional`` 上下文：跳过 ``None`` 成员后，剩余成员全部必须是 Path 类型。
        return all(
            arg is type(None) or _is_path_or_list_annotation(arg)
            for arg in get_args(annotation)
        )

    if annotation is pathlib.Path:
        return True

    if origin is list:
        args = get_args(annotation)
        return len(args) == 1 and args[0] is pathlib.Path

    return False


class APIRoute[T](BaseModel):
    """接口基类，纯数据类（字段 + 路由元数据）。

    通过泛型 ``T`` 指定 JSON 响应校验类型。
    仅当响应 content-type 为 JSON 时，
    框架会用 Pydantic ``TypeAdapter`` 按 ``T`` 校验 JSON 内容。

    实际请求由 ``Client.send(api_route)`` 发起。

    :var _dependant: 路由元数据和参数依赖定义缓存。
    :vartype _dependant: ClassVar[Dependant | None]

    Example::

        @router.get(path="/users")
        class GetUsers(APIRoute[list[UserData]]):
            limit: Annotated[int, Query()] = Field(ge=1, le=100, default=20)

        endpoint = GetUsers(limit=10)
        response = client.send(endpoint)  # 类型: Response[list[UserData]]
        if response.raw.status == 200:
            users = response.validated  # 类型: list[UserData] | None
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

        分类逻辑（按优先级顺序匹配）：

        1. **Param 标记分发**（``Annotated[Type, Path() / Query() / Header() /
           Body() / Form()]``）：按 ``param_info.in_`` 属性归类到对应列表。

        2. **路径占位符兜底**（无 Param 标记时）：若字段 alias 出现在
           路由路径 ``{...}`` 占位符中，则归类为 path_params。

        3. **类型推断三分支**（无 Param 标记时）：

           - ``UploadFile`` / ``list[UploadFile]``（含 Optional 包装） →
             file_body_params
           - 复杂类型（BaseModel / Mapping / 序列 / dataclass） →
             pure_body_params
           - 标量类型（int / str / bool / float 等） → query_params

        互斥约束：``pure_body_params`` 不可与 ``form_body_params`` 或
        ``file_body_params`` 共存，否则在构建 ``Dependant`` 时抛出
        ``ValueError``。

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
            pure_body_params: list[ModelField] = []
            form_body_params: list[ModelField] = []
            file_body_params: list[ModelField] = []

            # 使用正则表达式提取路径参数名（参考 FastAPI loose regex，支持 kebab-case 等）
            path_param_names = set(re.findall(r"\{(.*?)\}", path))

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
                        if isinstance(param_info, Form):
                            # Form-marked 文件类型（UploadFile / pathlib.Path）应路由到 file_body_params
                            field_type = field_info.annotation
                            if _is_path_or_list_annotation(field_type) or _is_uploadfile_or_list_annotation(field_type):
                                file_body_params.append(model_field)
                            else:
                                form_body_params.append(model_field)
                        else:
                            pure_body_params.append(model_field)
                    continue

                # 路径占位符兜底（无 Param 标记时）
                if model_field.alias in path_param_names:
                    path_params.append(model_field)
                    continue

                # 类型推断三分支（无 Param 标记时）：
                #   UploadFile / list[UploadFile]（含 Optional） → file_body_params
                #   复杂类型（BaseModel/Mapping/序列/dataclass） → pure_body_params
                #   标量类型（int/str/bool/float 等） → query_params
                field_type = field_info.annotation
                if _is_uploadfile_or_list_annotation(field_type):
                    file_body_params.append(model_field)
                elif field_annotation_is_complex(field_type):
                    pure_body_params.append(model_field)
                else:
                    query_params.append(model_field)

            # 提取响应类型（用于 JSON 响应校验）
            json_response_schema: type | None = None
            for c in cls.mro():
                name = c.__name__
                if name == "APIRoute":
                    # APIRoute 不带泛型参数，无需校验响应
                    break
                if name.startswith("APIRoute["):
                    metadata = getattr(c, "__pydantic_generic_metadata__", {})
                    if args := metadata.get("args"):
                        json_response_schema = args[0]  # 如果泛型有多个参数，取第一个作为响应类型，忽略后续其他参数
                    break

            # 创建 JSON 响应校验器
            json_response_schema_adapter: TypeAdapter[Any] | None = None
            if json_response_schema is not None:
                json_response_schema_adapter = TypeAdapter(json_response_schema)

            cls._dependant = Dependant(
                method=method,
                path=path,
                path_params=path_params,
                query_params=query_params,
                header_params=header_params,
                pure_body_params=pure_body_params,
                form_body_params=form_body_params,
                file_body_params=file_body_params,
                json_response_schema=json_response_schema,
                json_response_schema_adapter=json_response_schema_adapter,
            )

            if cls._dependant.pure_body_params and (
                cls._dependant.form_body_params or cls._dependant.file_body_params
            ):
                raise ValueError("Body 与 Form/UploadFile 字段不能在同一 APIRoute 混用")

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
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE"],
    path: str,
) -> Callable[[type[T]], type[T]]:
    """类装饰器工厂函数，用于注入路由元数据到接口类。

    在类定义处通过装饰器语法传入 HTTP 方法和路径。
    被装饰的类必须继承自 APIRoute。

    :param method: HTTP 方法，必须是 GET、POST、PUT、PATCH、DELETE、HEAD、OPTIONS、TRACE 之一。
    :type method: Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE"]
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

    提供类似 FastAPI 风格的路由装饰器方法（get/post/put/patch/delete/head/options/trace），
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

        @router.head("/users")
        class HeadUsers(APIRoute[dict]):
            pass

        @router.options("/users")
        class OptionsUsers(APIRoute[dict]):
            pass

        @router.trace("/users")
        class TraceUsers(APIRoute[dict]):
            pass
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

    def put[T: APIRoute](
        self,
        path: str,
    ) -> Callable[[type[T]], type[T]]:
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

    def head[T: APIRoute](self, path: str) -> Callable[[type[T]], type[T]]:
        """HEAD 请求装饰器。

        :param path: 接口路径，支持路径参数占位符（如 /users/{user_id}）。
        :type path: str
        :return: 类装饰器函数。
        :rtype: Callable[[type[T]], type[T]]

        Example::

            @router.head("/users")
            class HeadUsers(APIRoute[dict]):
                pass
        """
        return api_route_decorator(method="HEAD", path=path)

    def options[T: APIRoute](self, path: str) -> Callable[[type[T]], type[T]]:
        """OPTIONS 请求装饰器。

        :param path: 接口路径，支持路径参数占位符（如 /users/{user_id}）。
        :type path: str
        :return: 类装饰器函数。
        :rtype: Callable[[type[T]], type[T]]

        Example::

            @router.options("/users")
            class OptionsUsers(APIRoute[dict]):
                pass
        """
        return api_route_decorator(method="OPTIONS", path=path)

    def trace[T: APIRoute](self, path: str) -> Callable[[type[T]], type[T]]:
        """TRACE 请求装饰器。

        :param path: 接口路径，支持路径参数占位符（如 /users/{user_id}）。
        :type path: str
        :return: 类装饰器函数。
        :rtype: Callable[[type[T]], type[T]]

        Example::

            @router.trace("/users")
            class TraceUsers(APIRoute[dict]):
                pass
        """
        return api_route_decorator(method="TRACE", path=path)
