"""参数依赖模型定义。"""

from dataclasses import dataclass, field
from typing import Any

from pydantic import TypeAdapter
from pydantic.fields import FieldInfo

from stoma.params import Param


@dataclass(frozen=True)
class ModelField:
    """模型字段定义。

    表示一个字段的完整信息，包括名称、别名和类型。

    :var name: 字段名称。
    :vartype name: str
    :var field_info: Pydantic 字段信息。
    :vartype field_info: FieldInfo
    :var param_info: 显式的 Param 标记（如 Body/Query/Path），如果没有则为空。
    :vartype param_info: Param | None
    """

    name: str
    field_info: FieldInfo
    param_info: Param | None = None

    @property
    def alias(self) -> str:
        """获取字段别名（用于序列化 HTTP 请求参数）。

        优先级：serialization_alias > name

        :return: 字段别名，用于序列化和请求参数名称。
        :rtype: str
        """
        if self.field_info.serialization_alias:
            return self.field_info.serialization_alias
        return self.name


@dataclass(frozen=True)
class Dependant:
    """路由端点参数依赖定义。

    表示一个路由端点的完整元数据，包含路由信息和参数依赖分析结果。
    `frozen=True` 确保对象不可变，线程安全。

    :var method: HTTP 方法（GET / POST / PUT / PATCH / DELETE / HEAD / OPTIONS / TRACE）。
    :vartype method: str
    :var path: 路由路径，如 /users/{user_id}。
    :vartype path: str
    :var path_params: 路径参数字段列表。
    :vartype path_params: list[ModelField]
    :var query_params: 查询参数字段列表。
    :vartype query_params: list[ModelField]
    :var header_params: 请求头参数字段列表。
    :vartype header_params: list[ModelField]
    :var pure_body_params: JSON 请求体参数字段列表（application/json）。
    :vartype pure_body_params: list[ModelField]
    :var form_body_params: Form 请求体参数字段列表（application/x-www-form-urlencoded 或 multipart/form-data）。
    :vartype form_body_params: list[ModelField]
    :var file_body_params: 上传文件请求体参数字段列表（UploadFile 或 list[UploadFile]）。
    :vartype file_body_params: list[ModelField]
    :var json_response_schema: JSON 响应校验类型，为 None 时表示不校验响应。
    :vartype json_response_schema: type | None
    :var json_response_schema_adapter: JSON 响应校验器缓存。
    :vartype json_response_schema_adapter: TypeAdapter | None
    :var upload_as_multipart: 上传文件时是否以 multipart/form-data 形式发送。默认 True。
        False 表示按照 Postman body 为 binary 形式发送，适用于单文件上传接口。
    :vartype upload_as_multipart: bool
    """

    method: str
    path: str
    path_params: list[ModelField] = field(default_factory=list)
    query_params: list[ModelField] = field(default_factory=list)
    header_params: list[ModelField] = field(default_factory=list)
    pure_body_params: list[ModelField] = field(default_factory=list)
    form_body_params: list[ModelField] = field(default_factory=list)
    file_body_params: list[ModelField] = field(default_factory=list)
    json_response_schema: type | None = None
    upload_as_multipart: bool = field(default=True)
    json_response_schema_adapter: TypeAdapter[Any] | None = None
