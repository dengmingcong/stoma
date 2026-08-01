"""参数依赖模型定义。"""

from dataclasses import dataclass, field
from typing import Any

from pydantic import TypeAdapter
from pydantic.fields import FieldInfo

from src.params import Param


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
        """获取字段别名。

        优先级：field_info.alias > name

        :return: 字段别名，用于序列化和请求参数名称。
        :rtype: str
        """
        # 使用 field_info 中的 alias
        if self.field_info.alias:
            return self.field_info.alias

        # 最后使用字段名称
        return self.name


@dataclass(frozen=True)
class Dependant:
    """路由端点参数依赖定义。

    表示一个路由端点的完整元数据，包含路由信息和参数依赖分析结果。
    `frozen=True` 确保对象不可变，线程安全。

    :var method: HTTP 方法（GET、POST、PUT、PATCH、DELETE 等）。
    :vartype method: str
    :var path: 路由路径，如 /users/{user_id}。
    :vartype path: str
    :var path_params: 路径参数字段列表。
    :vartype path_params: list[ModelField]
    :var query_params: 查询参数字段列表。
    :vartype query_params: list[ModelField]
    :var header_params: 请求头参数字段列表。
    :vartype header_params: list[ModelField]
    :var body_params: 请求体参数字段列表。
    :vartype body_params: list[ModelField]
    :var response_type: 响应数据类型。
    :vartype response_type: type | None
    :var response_type_adapter: 响应类型验证器缓存。
    :vartype response_type_adapter: TypeAdapter | None
    """

    method: str
    path: str
    path_params: list[ModelField] = field(default_factory=list)
    query_params: list[ModelField] = field(default_factory=list)
    header_params: list[ModelField] = field(default_factory=list)
    body_params: list[ModelField] = field(default_factory=list)
    response_type: type | None = None
    response_type_adapter: TypeAdapter[Any] | None = None
