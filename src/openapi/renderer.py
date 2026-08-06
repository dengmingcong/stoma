"""Endpoint 路由文件渲染器。

把 OpenAPI 端点（:class:`src.openapi.models.Endpoint`）渲染成 ``route.py``
文件。**模型类由 ``datamodel-code-generator`` 在前置阶段生成**，本模块
只负责：

- 解析路径 / 查询 / 头部参数并渲染为 Pydantic 字段声明
- 解析请求体引用哪个模型（名字符串）
- 解析响应引用哪个模型（名字符串）
- 检测 embed wrapper 并渲染 ``Annotated[..., Body(embed=True)]`` 装饰
- 输出 ``from .models import ...`` 导入

所有 schema → model 转换都在 :mod:`src.openapi.parser` 的
``_fill_schema_titles`` 阶段完成（注入 title 字段）；本模块不写 Pydantic
类定义，也不再做 spec 变换。Embed wrapper 的检测在渲染阶段就地完成，
不依赖任何中间数据结构（如 ``EmbedInfo``）。
"""

from __future__ import annotations

import keyword
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, Template
from openapi_pydantic.v3.v3_0 import Schema as Schema30
from openapi_pydantic.v3.v3_1 import Schema as Schema31
from pydantic.alias_generators import to_snake

from src.openapi.models import Endpoint, Parameter, RequestBody, Response

Schema = Schema30 | Schema31


@dataclass(frozen=True)
class ResolvedType:
    """schema 解析结果：字段类型表达式 + 需要的 import 列表。

    :var type_expr: 用于字段注解的类型字符串，如 ``"User"`` /
        ``"list[User]"`` / ``"dict[str, Any]"`` / ``""``。
    :vartype type_expr: str
    :var imports: 需要从 ``.models`` 导入的类名（元组）。空表示无 import。
    :vartype imports: tuple[str, ...]
    """

    type_expr: str
    imports: tuple[str, ...] = ()


def _is_snake_case(name: str) -> bool:
    """检测 name 是否已经是合法的 snake_case（且不是 Python 关键字）。"""
    if not name:
        return False
    if keyword.iskeyword(name):
        return False
    return bool(re.fullmatch(r"[a-z][a-z0-9_]*", name))


def _to_field_name(name: str) -> str:
    """将 OpenAPI 参数名转为合法的 snake_case field 名。"""
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_") or "param"
    if cleaned[0].isdigit():
        cleaned = f"n_{cleaned}"
    if keyword.iskeyword(cleaned):
        cleaned = f"p_{cleaned}"
    return to_snake(cleaned)


def _to_pascal_case(operation_id: str) -> str:
    """将 operationId 转换为 PascalCase 类名。"""
    normalized = operation_id.replace("-", "_")
    words = re.split(r"[_-]+|(?<=[a-z0-9])(?=[A-Z])", normalized)
    return "".join(word.capitalize() for word in words if word)


def _resolve_model_name(schema: Schema, default_name: str) -> ResolvedType:
    """从 Schema 解析出 :class:`ResolvedType`。

    规则：

    - ``$ref`` / 有 ``title`` → ``type_expr`` 是 schema 名，``imports`` 包含它
    - inline object（无 title）→ ``type_expr`` 是 ``default_name``，
      ``imports`` 包含 ``default_name``
    - array → ``type_expr`` 是 ``list[<items>]``，``imports`` 包含 items 名
    - 标量 → ``type_expr`` 是 ``"dict[str, Any]"``，``imports`` 为空
    """
    if schema.title:
        return ResolvedType(type_expr=schema.title, imports=(schema.title,))
    if schema.type == "array" and schema.items is not None and isinstance(schema.items, Schema):
        items_name = schema.items.title if schema.items.title else default_name
        return ResolvedType(type_expr=f"list[{items_name}]", imports=(items_name,))
    if schema.type == "object" and not schema.properties:
        return ResolvedType(type_expr="dict[str, Any]", imports=())
    return ResolvedType(type_expr=default_name, imports=(default_name,))


class EndpointRenderer:
    """Endpoint 路由文件渲染器。"""

    def __init__(
        self,
        template_path: str | Path | None = None,
    ) -> None:
        """初始化渲染器。

        :param template_path: 模板目录路径，默认为 ``openapi/templates/``。
        """
        if template_path is None:
            template_path = Path(__file__).parent / "templates"
        self.template_dir = Path(template_path)
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, endpoint: Endpoint) -> str:
        """渲染 endpoint 的 route.py 内容。

        :param endpoint: :class:`Endpoint` IR 对象。
        :return: 渲染后的 Python 源码字符串。
        """
        class_name = _to_pascal_case(endpoint.operation_id)
        response_resolved = self._extract_response_info(endpoint.responses, class_name)
        request_body_info = self._extract_request_body_info(endpoint.request_body, class_name)
        header_fields, param_fields = self._extract_params(endpoint.parameters)

        imported_models: list[str] = []
        imported_models.extend(response_resolved.imports)
        imported_models.extend(request_body_info["imports"])

        template: Template = self.env.get_template("endpoint.py.jinja2")
        return template.render(
            operation_id=endpoint.operation_id,
            class_name=class_name,
            method=endpoint.method,
            path=endpoint.path,
            summary=endpoint.summary,
            description=endpoint.description,
            response_type=response_resolved.type_expr,
            request_body_type=request_body_info["type"],
            request_body_embed=request_body_info["embed"],
            request_body_field_name=request_body_info["field_name"] or "body",
            header_fields=header_fields,
            param_fields=param_fields,
            imported_models=imported_models,
        )

    def _extract_params(
        self,
        parameters: list[Parameter],
    ) -> tuple[list[str], list[str]]:
        """提取参数信息（query/header/path），仍由 renderer 渲染为字段声明。

        :param parameters: OpenAPI 参数列表。
        :return: ``(Header 字段声明列表, Query/Path 字段声明列表)``。
        """
        header_fields: list[str] = []
        param_fields: list[str] = []

        for param in parameters:
            name = param.name or ""
            param_in = param.param_in
            location = param_in.value if param_in else "query"
            required = param.required or False
            schema = param.param_schema

            schema_dict = schema.model_dump(mode="json") if schema else {}
            json_type = schema_dict.get("type", "Any")
            param_type = _map_json_schema_type(str(json_type))

            field_line = _build_param_field_line(name, param_type, required, location)

            if location == "header":
                header_fields.append(field_line)
            else:
                param_fields.append(field_line)

        return header_fields, param_fields

    def _extract_request_body_info(
        self,
        request_body: RequestBody | None,
        class_name: str,
    ) -> dict[str, Any]:
        """提取请求体信息。

        行为：

        - 引用 ``components.schemas`` 或有 ``title`` 的 schema → ``type`` 等于
          schema 名（``models.py`` 中已有同名类），``imports`` 包含它。
        - embed wrapper（最外层是单属性 required object）→ ``embed=True``，
          ``field_name`` 用 wrapper 字段名，``type`` / ``imports`` 用内层 schema。
        - 未匹配 → ``type`` 为空字符串，``imports`` 为空（不生成 body 字段）。

        :param request_body: :class:`RequestBody` 对象。
        :param class_name: 接口类名，做 fallback。
        :return: ``{"type": str, "embed": bool, "field_name": str | None, "imports": tuple[str, ...]}``。
        """
        if not request_body:
            return {"type": "", "embed": False, "field_name": None, "imports": ()}

        content = request_body.content or {}
        json_media_type_obj = content.get("application/json", {})
        json_media_type_schema = getattr(json_media_type_obj, "media_type_schema", None)
        if not isinstance(json_media_type_schema, Schema):
            return {"type": "", "embed": False, "field_name": None, "imports": ()}

        embed = self._detect_embed(json_media_type_schema)
        if embed:
            return {
                "type": embed["type_expr"],
                "embed": True,
                "field_name": embed["field_name"],
                "imports": embed["imports"],
            }

        resolved = _resolve_model_name(json_media_type_schema, f"{class_name}Request")
        return {
            "type": resolved.type_expr,
            "embed": False,
            "field_name": None,
            "imports": resolved.imports,
        }

    def _detect_embed(self, json_media_type_schema: Schema) -> dict[str, Any] | None:
        """检测 schema 是否是最外层 embed wrapper。

        embed wrapper 的特征（OpenAPI 单属性 + required 的约定）：

        - ``type: object``
        - 有且仅有一个 property
        - 这个 property 在 ``required`` 列表中

        只检测最外层——runtime 也只用最外层 ``field_name`` 构造 body，中间层
        wrapper 对 runtime 无意义。

        :param json_media_type_schema: 待检测的 JSON Media Type Schema 对象。
        :return: ``{"field_name", "type_expr", "imports"}`` 或 ``None``。
        """
        if not isinstance(json_media_type_schema, Schema) or json_media_type_schema.type != "object":
            return None
        properties = json_media_type_schema.properties
        if not isinstance(properties, dict) or len(properties) != 1:
            return None
        required = json_media_type_schema.required or []
        if not isinstance(required, list):
            return None
        field_name, inner = next(iter(properties.items()))
        if field_name not in required or not isinstance(inner, Schema):
            return None
        resolved = _resolve_model_name(inner, "")
        return {
            "field_name": field_name,
            "type_expr": resolved.type_expr,
            "imports": resolved.imports,
        }

    def _extract_response_info(
        self,
        responses: dict[str, Response] | None,
        class_name: str,
    ) -> ResolvedType:
        """提取响应的 :class:`ResolvedType`（类型表达式 + import 列表）。

        :param responses: OpenAPI 响应字典。
        :param class_name: 接口类名，做 fallback。
        :return: 响应类型的 :class:`ResolvedType`，无响应时 ``type_expr=""``。
        """
        if not responses:
            return ResolvedType(type_expr="")

        response_200 = responses.get("200") or responses.get("201")
        if not response_200:
            return ResolvedType(type_expr="")

        content = response_200.content or {}
        json_content = content.get("application/json")
        if not json_content:
            return ResolvedType(type_expr="")

        schema = getattr(json_content, "media_type_schema", None)
        if not isinstance(schema, Schema):
            return ResolvedType(type_expr="")

        default_name = f"{class_name}Response" if class_name else ""
        return _resolve_model_name(schema, default_name)


def _map_json_schema_type(json_type: str) -> str:
    """把 JSON Schema 类型映射为 Python 类型。"""
    return {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
        "array": "list",
        "object": "dict",
    }.get(json_type, json_type)


def _build_param_field_line(
    name: str,
    param_type: str,
    required: bool,
    location: str,
) -> str:
    """构建参数（query / path / header）字段声明字符串。

    Header 字段使用 ``Annotated[..., Header()]``；非 snake_case 参数名
    转 snake_case 后保留原名作为 ``serialization_alias``。

    :param name: 原始 OpenAPI 参数名。
    :param param_type: Python 类型字符串。
    :param required: 是否必需。
    :param location: ``"header"`` / ``"query"`` / ``"path"``。
    :return: 字段声明字符串。
    """
    is_header = location == "header"
    is_snake = _is_snake_case(name)
    field_name = name if is_snake else _to_field_name(name)

    base_type = param_type if required else f"{param_type} | None"
    annotation = f"Annotated[{base_type}, Header()]" if is_header else base_type

    if is_snake:
        default = "" if required else " = None"
    elif required:
        default = f" = Field(serialization_alias={name!r})"
    else:
        default = f" = Field(default=None, serialization_alias={name!r})"

    return f"{field_name}: {annotation}{default}"


def render_to_file(
    output_dir: str | Path,
    operation_id: str,
    rendered_code: str,
) -> Path:
    """将渲染后的代码写入文件（snake_case operation_id → ``<op>.py``）。

    :param output_dir: 输出目录。
    :param operation_id: operationId。
    :param rendered_code: 渲染后的 Python 代码。
    :return: 写入的文件路径。
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    snake_name = _to_pascal_case(operation_id)
    snake_name = re.sub(r"([A-Z])", r"_\1", snake_name).lower().lstrip("_")
    file_name = f"{snake_name}.py"
    file_path = output_path / file_name
    file_path.write_text(rendered_code, encoding="utf-8")
    return file_path
