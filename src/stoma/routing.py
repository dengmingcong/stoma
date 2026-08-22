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
from typing import Annotated, ClassVar, Literal, get_args, get_origin

from pydantic import BaseModel, ConfigDict

from stoma.dependencies import Dependant, ModelField
from stoma.dependencies.annotation import (
    field_annotation_is_complex,
    is_uploadfile_or_list_annotation,
    validate_binary_body_annotation,
    validate_form_field_annotation,
)
from stoma.params import Form, Param, ParamTypes


class APIRoute(BaseModel):
    """接口基类，纯数据类（字段 + 路由元数据）。

    通过 ``@property`` 声明每个合法响应分支的协议，
    例如 ``on_200`` 返回 ``JSONResponseSpec`` 实例。
    客户端发送请求后通过 ``response.expect(endpoint.on_200)`` 选取响应协议。

    实际请求由 ``Client.send(api_route)`` 发起。

    :var _dependant: 路由元数据和参数依赖定义缓存。
    :vartype _dependant: ClassVar[Dependant | None]

    Example::

        @router.get(path="/users")
        class GetUsers(APIRoute):
            @property
            def on_200(self) -> JSONResponseSpec[list[UserData]]:
                return JSONResponseSpec(status_code=200, media_type="application/json", model=list[UserData])

            @property
            def on_404(self) -> JSONResponseSpec[ErrorResponse]:
                return JSONResponseSpec(status_code=404, media_type="application/json", model=ErrorResponse)

            @property
            def on_default(self) -> JSONResponseSpec[ErrorResponse]:
                return JSONResponseSpec(
                    status_code=lambda c: c not in [200, 404],
                    media_type="application/json",
                    model=ErrorResponse,
                )

            limit: Annotated[int, Query()] = Field(ge=1, le=100, default=20)

        endpoint = GetUsers(limit=10)
        response = client.send(endpoint)
        users = response.expect(GetUsers.on_200)  # 类型: list[UserData]
    """

    # Ref: https://pydantic.dev/docs/validation/latest/concepts/models/#class-variables
    _dependant: ClassVar[Dependant | None] = None
    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

    @classmethod
    def _get_dependant(
        cls,
        method: str | None = None,
        path: str | None = None,
        upload_as_multipart: bool = True,
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
        :param upload_as_multipart: 上传文件时是否以 multipart/form-data 形式发送。默认为 True。
        :type upload_as_multipart: bool
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
                            validate_form_field_annotation(field_info.annotation)
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
                #   标量类型（int / str / bool / float 等） → query_params
                field_type = field_info.annotation
                if is_uploadfile_or_list_annotation(field_type):
                    file_body_params.append(model_field)
                elif field_annotation_is_complex(field_type):
                    pure_body_params.append(model_field)
                else:
                    query_params.append(model_field)

            cls._dependant = Dependant(
                method=method,
                path=path,
                path_params=path_params,
                query_params=query_params,
                header_params=header_params,
                pure_body_params=pure_body_params,
                form_body_params=form_body_params,
                file_body_params=file_body_params,
                upload_as_multipart=upload_as_multipart,
            )

            if cls._dependant.pure_body_params and (cls._dependant.form_body_params or cls._dependant.file_body_params):
                raise ValueError("Body 与 Form/UploadFile 字段不能在同一 APIRoute 混用")

            if not upload_as_multipart:
                if len(cls._dependant.file_body_params) != 1:
                    raise ValueError(
                        f"upload_as_multipart=False 要求 body 恰好包含一个 UploadFile 字段，"
                        f"实际有 {len(cls._dependant.file_body_params)} 个"
                    )
                field = cls._dependant.file_body_params[0]
                validate_binary_body_annotation(field.field_info.annotation, field_name=field.name)
                if cls._dependant.form_body_params:
                    raise ValueError("upload_as_multipart=False 时不允许 Form 字段")
                if cls._dependant.pure_body_params:
                    raise ValueError("upload_as_multipart=False 时不允许 Body() 字段")

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
    upload_as_multipart: bool = True,
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

        from stoma import JSONResponseSpec

        @api_route_decorator(method="GET", path="/users/{user_id}")
        class GetUserById(APIRoute):
            @property
            def on_200(self) -> JSONResponseSpec[UserData]:
                return JSONResponseSpec(status_code=200, media_type="application/json", model=UserData)

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
        cls._get_dependant(method=method, path=path, upload_as_multipart=upload_as_multipart)
        return cls

    return update_api_route


class APIRouter:
    """路由器，提供便捷的路由装饰器方法。

    提供类似 FastAPI 风格的路由装饰器方法（get/post/put/patch/delete/head/options/trace），
    简化接口定义语法。

    :var prefix: 应用于所有路由方法的路径前缀。默认为 ``None``（falsy 值如 ``None`` / ``""`` 均不加前缀）。
        由该 router 装饰的 endpoint 最终路径为 ``self.prefix + path``，由调用方负责
        提供合法前缀（如 ``"/api/v3"``），框架不做归一化（如去除尾部斜杠）。
    :vartype prefix: str

    Example::

        from stoma import JSONResponseSpec

        # 创建路由器
        router = APIRouter()

        # 使用装饰器定义接口
        @router.get("/users")
        class GetUsers(APIRoute):
            @property
            def on_200(self) -> JSONResponseSpec[list[UserData]]:
                return JSONResponseSpec(status_code=200, media_type="application/json", model=list[UserData])

            limit: int = 20

        @router.post("/users")
        class CreateUser(APIRoute):
            @property
            def on_201(self) -> JSONResponseSpec[UserData]:
                return JSONResponseSpec(status_code=201, media_type="application/json", model=UserData)

            name: str
            email: str

        @router.head("/users")
        class HeadUsers(APIRoute):
            @property
            def on_200(self) -> JSONResponseSpec[dict]:
                return JSONResponseSpec(status_code=200, media_type="application/json", model=dict)

        @router.options("/users")
        class OptionsUsers(APIRoute):
            @property
            def on_200(self) -> JSONResponseSpec[dict]:
                return JSONResponseSpec(status_code=200, media_type="application/json", model=dict)

        @router.trace("/users")
        class TraceUsers(APIRoute):
            @property
            def on_200(self) -> JSONResponseSpec[dict]:
                return JSONResponseSpec(status_code=200, media_type="application/json", model=dict)

        # 创建带前缀的路由器：endpoint 实际路径为 prefix + 方法传入的 path
        router_v3 = APIRouter(prefix="/api/v3")

        @router_v3.get("/store/inventory")
        class GetInventory(APIRoute):
            @property
            def on_200(self) -> JSONResponseSpec[dict]:
                return JSONResponseSpec(status_code=200, media_type="application/json", model=dict)

        # GetInventory._get_dependant().path == "/api/v3/store/inventory"
    """

    def __init__(self, prefix: str | None = None) -> None:
        """初始化路由器。

        :param prefix: 应用于所有路由方法的路径前缀。默认为 ``None``（falsy 值如 ``None`` / ``""`` 均不加前缀）。
            由调用方负责提供合法前缀（如 ``"/api/v3"``），框架不做归一化（如去除尾部斜杠）。
        """
        self.prefix = prefix or ""

    def get[T: APIRoute](self, path: str, *, upload_as_multipart: bool = True) -> Callable[[type[T]], type[T]]:
        """GET 请求装饰器。

        :param path: 接口路径，支持路径参数占位符（如 ``/users/{user_id}``）。
            **必须以 ``/`` 开头**（如 ``/users``），由调用方保证。
            实际注入到 ``Dependant.path`` 的路径为 ``self.prefix + path``。
        :type path: str
        :param upload_as_multipart: 是否将请求作为 multipart/form-data 解析。默认为 True。
        :type upload_as_multipart: bool
        :return: 类装饰器函数。
        :rtype: Callable[[type[T]], type[T]]

        Example::

            from stoma import JSONResponseSpec

            # 无前缀：实际路径为 /users
            @router.get("/users")
            class GetUsers(APIRoute):
                @property
                def on_200(self) -> JSONResponseSpec[list[UserData]]:
                    return JSONResponseSpec(status_code=200, media_type="application/json", model=list[UserData])

                limit: int = 20

            # 带前缀：实际路径为 /api/v3/users/{user_id}
            @router_v3.get("/users/{user_id}")
            class GetUserV3(APIRoute):
                @property
                def on_200(self) -> JSONResponseSpec[UserData]:
                    return JSONResponseSpec(status_code=200, media_type="application/json", model=UserData)

                user_id: Annotated[int, Path()]
        """
        return api_route_decorator(method="GET", path=self.prefix + path, upload_as_multipart=upload_as_multipart)

    def post[T: APIRoute](self, path: str, *, upload_as_multipart: bool = True) -> Callable[[type[T]], type[T]]:
        """POST 请求装饰器。

        :param path: 接口路径，支持路径参数占位符（如 ``/users/{user_id}``）。
            **必须以 ``/`` 开头**（如 ``/users``），由调用方保证。
            实际注入到 ``Dependant.path`` 的路径为 ``self.prefix + path``。
        :type path: str
        :param upload_as_multipart: 是否将请求作为 multipart/form-data 解析。默认为 True。
        :type upload_as_multipart: bool
        :return: 类装饰器函数。
        :rtype: Callable[[type[T]], type[T]]

        Example::

            from stoma import JSONResponseSpec

            # 无前缀
            @router.post("/users")
            class CreateUser(APIRoute):
                @property
                def on_201(self) -> JSONResponseSpec[UserData]:
                    return JSONResponseSpec(status_code=201, media_type="application/json", model=UserData)

                name: str
                email: str

            # 带前缀：实际路径为 /api/v3/users
            @router_v3.post("/users")
            class CreateUserV3(APIRoute):
                @property
                def on_201(self) -> JSONResponseSpec[UserData]:
                    return JSONResponseSpec(status_code=201, media_type="application/json", model=UserData)

                name: str
                email: str
        """
        return api_route_decorator(method="POST", path=self.prefix + path, upload_as_multipart=upload_as_multipart)

    def put[T: APIRoute](
        self,
        path: str,
        *,
        upload_as_multipart: bool = True,
    ) -> Callable[[type[T]], type[T]]:
        """PUT 请求装饰器。

        :param path: 接口路径，支持路径参数占位符（如 ``/users/{user_id}``）。
            **必须以 ``/`` 开头**（如 ``/users``），由调用方保证。
            实际注入到 ``Dependant.path`` 的路径为 ``self.prefix + path``。
        :type path: str
        :param upload_as_multipart: 是否将请求作为 multipart/form-data 解析。默认为 True。
        :type upload_as_multipart: bool
        :return: 类装饰器函数。
        :rtype: Callable[[type[T]], type[T]]

        Example::

            from stoma import JSONResponseSpec

            # 无前缀
            @router.put("/users/{user_id}")
            class UpdateUser(APIRoute):
                @property
                def on_200(self) -> JSONResponseSpec[UserData]:
                    return JSONResponseSpec(status_code=200, media_type="application/json", model=UserData)

                user_id: Annotated[int, Path()]
                name: str

            # 带前缀：实际路径为 /api/v3/users/{user_id}
            @router_v3.put("/users/{user_id}")
            class UpdateUserV3(APIRoute):
                @property
                def on_200(self) -> JSONResponseSpec[UserData]:
                    return JSONResponseSpec(status_code=200, media_type="application/json", model=UserData)

                user_id: Annotated[int, Path()]
                name: str
        """
        return api_route_decorator(method="PUT", path=self.prefix + path, upload_as_multipart=upload_as_multipart)

    def patch[T: APIRoute](self, path: str, *, upload_as_multipart: bool = True) -> Callable[[type[T]], type[T]]:
        """PATCH 请求装饰器。

        :param path: 接口路径，支持路径参数占位符（如 ``/users/{user_id}``）。
            **必须以 ``/`` 开头**（如 ``/users``），由调用方保证。
            实际注入到 ``Dependant.path`` 的路径为 ``self.prefix + path``。
        :type path: str
        :param upload_as_multipart: 是否将请求作为 multipart/form-data 解析。默认为 True。
        :type upload_as_multipart: bool
        :return: 类装饰器函数。
        :rtype: Callable[[type[T]], type[T]]

        Example::

            from stoma import JSONResponseSpec

            # 无前缀
            @router.patch("/users/{user_id}")
            class PatchUser(APIRoute):
                @property
                def on_200(self) -> JSONResponseSpec[UserData]:
                    return JSONResponseSpec(status_code=200, media_type="application/json", model=UserData)

                user_id: Annotated[int, Path()]
                email: str | None = None

            # 带前缀：实际路径为 /api/v3/users/{user_id}
            @router_v3.patch("/users/{user_id}")
            class PatchUserV3(APIRoute):
                @property
                def on_200(self) -> JSONResponseSpec[UserData]:
                    return JSONResponseSpec(status_code=200, media_type="application/json", model=UserData)

                user_id: Annotated[int, Path()]
                email: str | None = None
        """
        return api_route_decorator(method="PATCH", path=self.prefix + path, upload_as_multipart=upload_as_multipart)

    def delete[T: APIRoute](self, path: str, *, upload_as_multipart: bool = True) -> Callable[[type[T]], type[T]]:
        """DELETE 请求装饰器。

        :param path: 接口路径，支持路径参数占位符（如 ``/users/{user_id}``）。
            **必须以 ``/`` 开头**（如 ``/users``），由调用方保证。
            实际注入到 ``Dependant.path`` 的路径为 ``self.prefix + path``。
        :type path: str
        :param upload_as_multipart: 是否将请求作为 multipart/form-data 解析。默认为 True。
        :type upload_as_multipart: bool
        :return: 类装饰器函数。
        :rtype: Callable[[type[T]], type[T]]

        Example::

            from stoma import JSONResponseSpec

            # 无前缀
            @router.delete("/users/{user_id}")
            class DeleteUser(APIRoute):
                @property
                def on_200(self) -> JSONResponseSpec[dict[str, str]]:
                    return JSONResponseSpec(status_code=200, media_type="application/json", model=dict[str, str])

                user_id: Annotated[int, Path()]

            # 带前缀：实际路径为 /api/v3/users/{user_id}
            @router_v3.delete("/users/{user_id}")
            class DeleteUserV3(APIRoute):
                @property
                def on_200(self) -> JSONResponseSpec[dict[str, str]]:
                    return JSONResponseSpec(status_code=200, media_type="application/json", model=dict[str, str])

                user_id: Annotated[int, Path()]
        """
        return api_route_decorator(method="DELETE", path=self.prefix + path, upload_as_multipart=upload_as_multipart)

    def head[T: APIRoute](self, path: str, *, upload_as_multipart: bool = True) -> Callable[[type[T]], type[T]]:
        """HEAD 请求装饰器。

        :param path: 接口路径，支持路径参数占位符（如 ``/users/{user_id}``）。
            **必须以 ``/`` 开头**（如 ``/users``），由调用方保证。
            实际注入到 ``Dependant.path`` 的路径为 ``self.prefix + path``。
        :type path: str
        :param upload_as_multipart: 是否将请求作为 multipart/form-data 解析。默认为 True。
        :type upload_as_multipart: bool
        :return: 类装饰器函数。
        :rtype: Callable[[type[T]], type[T]]

        Example::

            from stoma import JSONResponseSpec

            # 无前缀
            @router.head("/users")
            class HeadUsers(APIRoute):
                @property
                def on_200(self) -> JSONResponseSpec[dict]:
                    return JSONResponseSpec(status_code=200, media_type="application/json", model=dict)

            # 带前缀：实际路径为 /api/v3/users
            @router_v3.head("/users")
            class HeadUsersV3(APIRoute):
                @property
                def on_200(self) -> JSONResponseSpec[dict]:
                    return JSONResponseSpec(status_code=200, media_type="application/json", model=dict)
        """
        return api_route_decorator(method="HEAD", path=self.prefix + path, upload_as_multipart=upload_as_multipart)

    def options[T: APIRoute](self, path: str, *, upload_as_multipart: bool = True) -> Callable[[type[T]], type[T]]:
        """OPTIONS 请求装饰器。

        :param path: 接口路径，支持路径参数占位符（如 ``/users/{user_id}``）。
            **必须以 ``/`` 开头**（如 ``/users``），由调用方保证。
            实际注入到 ``Dependant.path`` 的路径为 ``self.prefix + path``。
        :type path: str
        :param upload_as_multipart: 是否将请求作为 multipart/form-data 解析。默认为 True。
        :type upload_as_multipart: bool
        :return: 类装饰器函数。
        :rtype: Callable[[type[T]], type[T]]

        Example::

            from stoma import JSONResponseSpec

            # 无前缀
            @router.options("/users")
            class OptionsUsers(APIRoute):
                @property
                def on_200(self) -> JSONResponseSpec[dict]:
                    return JSONResponseSpec(status_code=200, media_type="application/json", model=dict)

            # 带前缀：实际路径为 /api/v3/users
            @router_v3.options("/users")
            class OptionsUsersV3(APIRoute):
                @property
                def on_200(self) -> JSONResponseSpec[dict]:
                    return JSONResponseSpec(status_code=200, media_type="application/json", model=dict)
        """
        return api_route_decorator(method="OPTIONS", path=self.prefix + path, upload_as_multipart=upload_as_multipart)

    def trace[T: APIRoute](self, path: str, *, upload_as_multipart: bool = True) -> Callable[[type[T]], type[T]]:
        """TRACE 请求装饰器。

        :param path: 接口路径，支持路径参数占位符（如 ``/users/{user_id}``）。
            **必须以 ``/`` 开头**（如 ``/users``），由调用方保证。
            实际注入到 ``Dependant.path`` 的路径为 ``self.prefix + path``。
        :type path: str
        :param upload_as_multipart: 是否将请求作为 multipart/form-data 解析。默认为 True。
        :type upload_as_multipart: bool
        :return: 类装饰器函数。
        :rtype: Callable[[type[T]], type[T]]

        Example::

            from stoma import JSONResponseSpec

            # 无前缀
            @router.trace("/users")
            class TraceUsers(APIRoute):
                @property
                def on_200(self) -> JSONResponseSpec[dict]:
                    return JSONResponseSpec(status_code=200, media_type="application/json", model=dict)

            # 带前缀：实际路径为 /api/v3/users
            @router_v3.trace("/users")
            class TraceUsersV3(APIRoute):
                @property
                def on_200(self) -> JSONResponseSpec[dict]:
                    return JSONResponseSpec(status_code=200, media_type="application/json", model=dict)
        """
        return api_route_decorator(method="TRACE", path=self.prefix + path, upload_as_multipart=upload_as_multipart)
