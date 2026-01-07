"""参数标记类型，参考 FastAPI 的实现方式。

此模块提供了用于标记接口参数来源的类型，包括：

- Query：查询参数
- Path：路径参数
- Header：请求头参数
- Body：请求体参数

这些类型的实现参考 FastAPI 的 `fastapi.params` 模块，确保参数验证逻辑、
与 Pydantic Field 的集成方式、参数元数据的存储和传递方式、
默认值/别名/验证器的处理逻辑与 FastAPI 保持一致。
"""

from collections.abc import Callable
from enum import Enum
from typing import Any

from pydantic import AliasChoices, AliasPath
from pydantic.fields import FieldInfo

# 使用 Pydantic 的 Undefined 作为未设置标记
_Unset: Any = ...


class ParamTypes(Enum):
    """参数类型枚举。"""

    query = "query"
    header = "header"
    path = "path"
    body = "body"


class Param(FieldInfo):  # type: ignore[misc]
    """参数基类，继承自 Pydantic 的 FieldInfo。

    参考 FastAPI 的 Param 类实现，提供与 Pydantic Field 的完整集成。

    :var in_: 参数类型（query/header/path/body）。
    :vartype in_: ParamTypes
    """

    in_: ParamTypes

    def __init__(
        self,
        default: Any = _Unset,
        *,
        default_factory: Callable[[], Any] | None = _Unset,
        annotation: Any | None = None,
        alias: str | None = None,
        alias_priority: int | None = _Unset,
        validation_alias: str | AliasPath | AliasChoices | None = None,
        serialization_alias: str | None = None,
        title: str | None = None,
        description: str | None = None,
        gt: float | None = None,
        ge: float | None = None,
        lt: float | None = None,
        le: float | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        pattern: str | None = None,
        discriminator: str | None = None,
        strict: bool | None = _Unset,
        multiple_of: float | None = _Unset,
        allow_inf_nan: bool | None = _Unset,
        max_digits: int | None = _Unset,
        decimal_places: int | None = _Unset,
        examples: list[Any] | None = None,
        deprecated: bool | None = None,
        include_in_schema: bool = True,
        json_schema_extra: dict[str, Any] | None = None,
        **extra: Any,
    ):
        """初始化参数。

        参数列表参考 FastAPI，支持完整的 Pydantic 验证功能。

        :param default: 默认值。
        :param default_factory: 默认值工厂函数。
        :param annotation: 类型注解。
        :param alias: 参数别名。
        :param alias_priority: 别名优先级。
        :param validation_alias: 验证时使用的别名。
        :param serialization_alias: 序列化时使用的别名。
        :param title: 参数标题。
        :param description: 参数描述。
        :param gt: 大于此值的验证器。
        :param ge: 大于等于此值的验证器。
        :param lt: 小于此值的验证器。
        :param le: 小于等于此值的验证器。
        :param min_length: 最小长度。
        :param max_length: 最大长度。
        :param pattern: 正则表达式模式。
        :param discriminator: 判别器字段。
        :param strict: 严格模式。
        :param multiple_of: 倍数验证。
        :param allow_inf_nan: 是否允许无穷大和 NaN。
        :param max_digits: 最大数字位数。
        :param decimal_places: 小数位数。
        :param examples: 示例值列表。
        :param deprecated: 是否已弃用。
        :param include_in_schema: 是否包含在 schema 中。
        :param json_schema_extra: 额外的 JSON schema 信息。
        :param **extra: 其他额外参数。
        """
        # 将 examples 添加到 json_schema_extra 中以便 Pydantic 处理
        if examples is not None:
            if json_schema_extra is None:
                json_schema_extra = {}
            json_schema_extra = {**json_schema_extra, "examples": examples}

        kwargs = dict(
            default=default,
            alias=alias,
            title=title,
            description=description,
            gt=gt,
            ge=ge,
            lt=lt,
            le=le,
            min_length=min_length,
            max_length=max_length,
            discriminator=discriminator,
            json_schema_extra=json_schema_extra,
            **extra,
        )

        # 只在非 _Unset 时添加这些参数
        if default_factory is not _Unset:
            kwargs["default_factory"] = default_factory
        if alias_priority is not _Unset:
            kwargs["alias_priority"] = alias_priority
        if validation_alias is not None:
            kwargs["validation_alias"] = validation_alias
        if serialization_alias is not None:
            kwargs["serialization_alias"] = serialization_alias
        if pattern is not None:
            kwargs["pattern"] = pattern
        if strict is not _Unset:
            kwargs["strict"] = strict
        if multiple_of is not _Unset:
            kwargs["multiple_of"] = multiple_of
        if allow_inf_nan is not _Unset:
            kwargs["allow_inf_nan"] = allow_inf_nan
        if max_digits is not _Unset:
            kwargs["max_digits"] = max_digits
        if decimal_places is not _Unset:
            kwargs["decimal_places"] = decimal_places

        # 调用父类构造函数
        super().__init__(annotation=annotation, **kwargs)

        # 在父类初始化之后设置我们的自定义属性
        # 这样可以避免被 Pydantic 的 FieldInfo 覆盖
        self.deprecated = deprecated
        self.include_in_schema = include_in_schema
        self.examples = examples


class Path(Param):  # type: ignore[misc]
    """路径参数标记。

    用于标记接口类中的路径参数字段。路径参数必须在路径模板中定义（如 /users/{user_id}），
    且始终是必需的。

    .. note::
        路径参数不提供 ``default`` 参数，因为路径参数始终是必需的。
        如需动态生成默认值，可使用 ``default_factory`` 参数。

    Example::

        from typing import Annotated
        from pydantic import BaseModel

        class GetUserById(BaseModel):
            user_id: Annotated[int, Path(description="用户 ID")]
    """

    in_ = ParamTypes.path

    def __init__(
        self,
        *,
        default_factory: Callable[[], Any] | None = _Unset,
        annotation: Any | None = None,
        alias: str | None = None,
        alias_priority: int | None = _Unset,
        validation_alias: str | AliasPath | AliasChoices | None = None,
        serialization_alias: str | None = None,
        title: str | None = None,
        description: str | None = None,
        gt: float | None = None,
        ge: float | None = None,
        lt: float | None = None,
        le: float | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        pattern: str | None = None,
        discriminator: str | None = None,
        strict: bool | None = _Unset,
        multiple_of: float | None = _Unset,
        allow_inf_nan: bool | None = _Unset,
        max_digits: int | None = _Unset,
        decimal_places: int | None = _Unset,
        examples: list[Any] | None = None,
        deprecated: bool | None = None,
        include_in_schema: bool = True,
        json_schema_extra: dict[str, Any] | None = None,
        **extra: Any,
    ):
        """初始化路径参数。

        路径参数始终是必需的，不接受 default 参数。
        如需动态生成默认值，可使用 ``default_factory`` 参数。
        """
        super().__init__(
            default=...,
            default_factory=default_factory,
            annotation=annotation,
            alias=alias,
            alias_priority=alias_priority,
            validation_alias=validation_alias,
            serialization_alias=serialization_alias,
            title=title,
            description=description,
            gt=gt,
            ge=ge,
            lt=lt,
            le=le,
            min_length=min_length,
            max_length=max_length,
            pattern=pattern,
            discriminator=discriminator,
            strict=strict,
            multiple_of=multiple_of,
            allow_inf_nan=allow_inf_nan,
            max_digits=max_digits,
            decimal_places=decimal_places,
            examples=examples,
            deprecated=deprecated,
            include_in_schema=include_in_schema,
            json_schema_extra=json_schema_extra,
            **extra,
        )


class Query(Param):  # type: ignore[misc]
    """查询参数标记。

    用于标记接口类中的查询参数字段。查询参数会附加在 URL 后面（如 ?limit=10&offset=0）。

    .. note::
        遵循 FastAPI 最佳实践，不提供 ``default`` 参数。
        应使用函数参数默认值来设置静态默认值，如需动态生成默认值可使用 ``default_factory``。

    Example::

        from typing import Annotated
        from pydantic import BaseModel

        class GetUsers(BaseModel):
            limit: Annotated[int, Query(ge=1, le=100)] = 20
            offset: Annotated[int, Query(ge=0)] = 0
            # 动态默认值示例
            timestamp: Annotated[float, Query(default_factory=time.time)]
    """

    in_ = ParamTypes.query

    def __init__(
        self,
        *,
        default_factory: Callable[[], Any] | None = _Unset,
        annotation: Any | None = None,
        alias: str | None = None,
        alias_priority: int | None = _Unset,
        validation_alias: str | AliasPath | AliasChoices | None = None,
        serialization_alias: str | None = None,
        title: str | None = None,
        description: str | None = None,
        gt: float | None = None,
        ge: float | None = None,
        lt: float | None = None,
        le: float | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        pattern: str | None = None,
        discriminator: str | None = None,
        strict: bool | None = _Unset,
        multiple_of: float | None = _Unset,
        allow_inf_nan: bool | None = _Unset,
        max_digits: int | None = _Unset,
        decimal_places: int | None = _Unset,
        examples: list[Any] | None = None,
        deprecated: bool | None = None,
        include_in_schema: bool = True,
        json_schema_extra: dict[str, Any] | None = None,
        **extra: Any,
    ):
        """初始化查询参数。

        不提供 ``default`` 参数，应使用函数参数默认值来设置默认值。
        如需动态生成默认值，可使用 ``default_factory`` 参数。
        """
        super().__init__(
            default=_Unset,
            default_factory=default_factory,
            annotation=annotation,
            alias=alias,
            alias_priority=alias_priority,
            validation_alias=validation_alias,
            serialization_alias=serialization_alias,
            title=title,
            description=description,
            gt=gt,
            ge=ge,
            lt=lt,
            le=le,
            min_length=min_length,
            max_length=max_length,
            pattern=pattern,
            discriminator=discriminator,
            strict=strict,
            multiple_of=multiple_of,
            allow_inf_nan=allow_inf_nan,
            max_digits=max_digits,
            decimal_places=decimal_places,
            examples=examples,
            deprecated=deprecated,
            include_in_schema=include_in_schema,
            json_schema_extra=json_schema_extra,
            **extra,
        )


class Header(Param):  # type: ignore[misc]
    """请求头参数标记。

    用于标记接口类中的请求头字段。请求头参数会从 HTTP 请求头中提取。

    :param convert_underscores: 是否将字段名中的下划线转换为连字符。default: True

    .. note::
        遵循 FastAPI 最佳实践，不提供 ``default`` 参数。
        应使用函数参数默认值来设置静态默认值，如需动态生成默认值可使用 ``default_factory``。

    Example::

        from typing import Annotated
        from pydantic import BaseModel

        class GetUsers(BaseModel):
            authorization: Annotated[str, Header(alias="Authorization")]
            user_agent: Annotated[str | None, Header()] = None
    """

    in_ = ParamTypes.header

    def __init__(
        self,
        *,
        default_factory: Callable[[], Any] | None = _Unset,
        annotation: Any | None = None,
        alias: str | None = None,
        alias_priority: int | None = _Unset,
        validation_alias: str | AliasPath | AliasChoices | None = None,
        serialization_alias: str | None = None,
        convert_underscores: bool = True,
        title: str | None = None,
        description: str | None = None,
        gt: float | None = None,
        ge: float | None = None,
        lt: float | None = None,
        le: float | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        pattern: str | None = None,
        discriminator: str | None = None,
        strict: bool | None = _Unset,
        multiple_of: float | None = _Unset,
        allow_inf_nan: bool | None = _Unset,
        max_digits: int | None = _Unset,
        decimal_places: int | None = _Unset,
        examples: list[Any] | None = None,
        deprecated: bool | None = None,
        include_in_schema: bool = True,
        json_schema_extra: dict[str, Any] | None = None,
        **extra: Any,
    ):
        """初始化请求头参数。

        :param convert_underscores: 是否将字段名中的下划线转换为连字符
            （如 user_agent → User-Agent）。

        不提供 ``default`` 参数，应使用函数参数默认值来设置默认值。
        如需动态生成默认值，可使用 ``default_factory`` 参数。
        """
        self.convert_underscores = convert_underscores
        super().__init__(
            default=_Unset,
            default_factory=default_factory,
            annotation=annotation,
            alias=alias,
            alias_priority=alias_priority,
            validation_alias=validation_alias,
            serialization_alias=serialization_alias,
            title=title,
            description=description,
            gt=gt,
            ge=ge,
            lt=lt,
            le=le,
            min_length=min_length,
            max_length=max_length,
            pattern=pattern,
            discriminator=discriminator,
            strict=strict,
            multiple_of=multiple_of,
            allow_inf_nan=allow_inf_nan,
            max_digits=max_digits,
            decimal_places=decimal_places,
            examples=examples,
            deprecated=deprecated,
            include_in_schema=include_in_schema,
            json_schema_extra=json_schema_extra,
            **extra,
        )


class Body(Param):  # type: ignore[misc]
    """请求体参数标记。

    用于标记接口类中的请求体字段。请求体会被序列化为 JSON 发送到服务器。

    :param embed: 是否嵌入单个字段。default: False
    :param media_type: 媒体类型。default: "application/json"

    .. note::
        遵循 FastAPI 最佳实践，不提供 ``default`` 参数。
        Body 参数通常是必需的，如需可选可使用函数参数默认值。
        如需动态生成默认值，可使用 ``default_factory`` 参数。

    Example::

        from typing import Annotated
        from pydantic import BaseModel

        class UserCreateRequest(BaseModel):
            name: str
            email: str

        class CreateUser(BaseModel):
            body: Annotated[UserCreateRequest, Body()]
    """

    in_ = ParamTypes.body

    def __init__(
        self,
        *,
        default_factory: Callable[[], Any] | None = _Unset,
        annotation: Any | None = None,
        embed: bool = False,
        media_type: str = "application/json",
        alias: str | None = None,
        alias_priority: int | None = _Unset,
        validation_alias: str | AliasPath | AliasChoices | None = None,
        serialization_alias: str | None = None,
        title: str | None = None,
        description: str | None = None,
        gt: float | None = None,
        ge: float | None = None,
        lt: float | None = None,
        le: float | None = None,
        min_length: int | None = None,
        max_length: int | None = None,
        pattern: str | None = None,
        discriminator: str | None = None,
        strict: bool | None = _Unset,
        multiple_of: float | None = _Unset,
        allow_inf_nan: bool | None = _Unset,
        max_digits: int | None = _Unset,
        decimal_places: int | None = _Unset,
        examples: list[Any] | None = None,
        deprecated: bool | None = None,
        include_in_schema: bool = True,
        json_schema_extra: dict[str, Any] | None = None,
        **extra: Any,
    ):
        """初始化请求体参数。

        :param embed: 是否将单个 Body 字段嵌入到对象中。
        :param media_type: 请求体的媒体类型。

        不提供 ``default`` 参数，应使用函数参数默认值来设置默认值。
        如需动态生成默认值，可使用 ``default_factory`` 参数。
        """
        self.embed = embed
        self.media_type = media_type
        super().__init__(
            default=_Unset,
            default_factory=default_factory,
            annotation=annotation,
            alias=alias,
            alias_priority=alias_priority,
            validation_alias=validation_alias,
            serialization_alias=serialization_alias,
            title=title,
            description=description,
            gt=gt,
            ge=ge,
            lt=lt,
            le=le,
            min_length=min_length,
            max_length=max_length,
            pattern=pattern,
            discriminator=discriminator,
            strict=strict,
            multiple_of=multiple_of,
            allow_inf_nan=allow_inf_nan,
            max_digits=max_digits,
            decimal_places=decimal_places,
            examples=examples,
            deprecated=deprecated,
            include_in_schema=include_in_schema,
            json_schema_extra=json_schema_extra,
            **extra,
        )


__all__ = ["Param", "ParamTypes", "Query", "Path", "Header", "Body"]
