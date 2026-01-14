"""参数依赖模型定义。"""

from dataclasses import dataclass

from pydantic.fields import FieldInfo

from src.params import Param


@dataclass(frozen=True)
class ModelField:
    """模型字段定义。

    表示一个字段的完整信息，包括名称、别名、类型和 Param 标记。

    :var name: 字段名称。
    :vartype name: str
    :var alias: 字段别名，用于序列化/请求参数名称。
    :vartype alias: str
    :var field_info: Pydantic 字段信息。
    :vartype field_info: FieldInfo
    :var param: 参数标记（Query、Path、Header、Body 等），可选。
    :vartype param: Param | None
    """

    name: str
    alias: str
    field_info: FieldInfo
    param: Param | None = None


@dataclass(frozen=True)
class Dependant:
    """路由端点参数依赖定义。

    表示一个路由端点的完整元数据，包含路由信息和参数依赖分析结果。
    `frozen=True` 确保对象不可变，线程安全。

    :var method: HTTP 方法（GET、POST、PUT、PATCH、DELETE 等）。
    :vartype method: str
    :var path: 路由路径，如 /users/{user_id}。
    :vartype path: str
    :var servers: 接口级别的服务器列表。
    :vartype servers: list[str] | None
    :var path_params: 路径参数字段列表。
    :vartype path_params: list[ModelField]
    :var query_params: 查询参数字段列表。
    :vartype query_params: list[ModelField]
    :var header_params: 请求头参数字段列表。
    :vartype header_params: list[ModelField]
    :var body_params: 请求体参数字段列表。
    :vartype body_params: list[ModelField]
    """

    method: str
    path: str
    servers: list[str] | None
    path_params: list[ModelField]
    query_params: list[ModelField]
    header_params: list[ModelField]
    body_params: list[ModelField]
