"""Endpoint 路由文件渲染器。

把 OpenAPI 端点（:class:`src.openapi.models.Endpoint`）渲染成 ``route.py``
文件。**模型类由 ``datamodel-code-generator`` 在前置阶段生成**，本模块
只负责：

- 解析路径 / 查询 / 头部参数并渲染为 Pydantic 字段声明
- 解析请求体引用哪个模型（名字符串）
- 解析响应引用哪个模型（名字符串）
- 输出 ``from .models import ...`` 导入

所有 schema → model 转换都在 :mod:`src.openapi.parser` 的 ``load()``
阶段（用 openapi-pydantic 构造 Pydantic 模型，$ref 字段是 ``Reference``）。
renderer 直接读 ``Reference.ref`` 字符串计算模型名。
"""

from __future__ import annotations

import keyword
import re
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template
from openapi_pydantic import Reference
from pydantic.alias_generators import to_snake

from src.openapi.models import Endpoint, Parameter, RequestBody, Response


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


def _resolve_endpoint_class_and_file(endpoint: Endpoint) -> tuple[str, str]:
    """解析 endpoint 的 APIRoute 类名与文件名。

    operationId 必填（由 :meth:`OpenAPIParser.validate_operation_ids` 保证），
    类名与文件名都从 operationId 派生。

    :param endpoint: :class:`Endpoint` IR 对象。
    :return: ``(class_name, file_name)`` 元组，``file_name`` 含 ``.py`` 后缀。
    """
    return _to_pascal_case(endpoint.operation_id), f"{to_snake(endpoint.operation_id)}.py"


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
        class_name, _ = _resolve_endpoint_class_and_file(endpoint)
        response_resolved = self._extract_response_info(endpoint.responses, endpoint)
        request_body_resolved = self._extract_request_body_info(endpoint.request_body, endpoint)
        header_fields, param_fields = self._extract_params(endpoint.parameters)

        imported_models: list[str] = []
        imported_models.extend(response_resolved.imports)
        imported_models.extend(request_body_resolved.imports)

        template: Template = self.env.get_template("endpoint.py.jinja2")
        return template.render(
            operation_id=endpoint.operation_id,
            class_name=class_name,
            method=endpoint.method,
            path=endpoint.path,
            summary=endpoint.summary,
            description=endpoint.description,
            response_type=response_resolved.type_expr,
            request_body_type=request_body_resolved.type_expr,
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

            if isinstance(schema, Reference):
                # $ref: 用 ref 末段作类型名（datamodel-codegen 也会这么做）
                param_type = schema.ref.rsplit("/", 1)[-1]
            else:
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
        endpoint: Endpoint,
    ) -> ResolvedType:
        """提取请求体的 :class:`ResolvedType`（类型表达式 + import 列表）。

        ``$ref`` 路径取末段并 PascalCase 化（对齐 ``datamodel-code-generator``
        对 ``components.schemas`` key 的自动 PascalCase 行为，例如
        ``user-profile`` → ``UserProfile``）；inline object 路径派生为
        ``{PascalOpId}Request``（对齐 ``datamodel-code-generator`` 的
        ``use_operation_id_as_name=True`` —— ``datamodel-code-generator``
        在该模式下对 inline request body 用 ``{operationId}Request`` 命名）。

        :param request_body: :class:`RequestBody` 对象。
        :param endpoint: 当前 :class:`Endpoint` IR 对象。
        :return: 请求体的 :class:`ResolvedType`。
        """
        if not request_body:
            return ResolvedType(type_expr="")

        content = request_body.content or {}
        json_content = content.get("application/json", {})
        schema = getattr(json_content, "media_type_schema", None)

        if isinstance(schema, Reference):
            name = _to_pascal_case(schema.ref.rsplit("/", 1)[-1])
            return ResolvedType(type_expr=name, imports=(name,))
        name = f"{_to_pascal_case(endpoint.operation_id)}Request"
        return ResolvedType(type_expr=name, imports=(name,))

    def _extract_response_info(
        self,
        responses: dict[str, Response] | None,
        endpoint: Endpoint,
    ) -> ResolvedType:
        """提取响应的 :class:`ResolvedType`（类型表达式 + import 列表）。

        ``$ref`` 路径取末段并 PascalCase 化（对齐 ``datamodel-code-generator``
        对 ``components.schemas`` key 的自动 PascalCase 行为，例如
        ``user-profile`` → ``UserProfile``）；inline object 路径派生为
        ``{PascalOpId}Response``（对齐 ``datamodel-code-generator`` 的
        ``use_operation_id_as_name=True`` —— ``datamodel-code-generator``
        在该模式下对 inline response 用 ``{operationId}Response`` 命名）。

        :param responses: OpenAPI 响应字典。
        :param endpoint: 当前 :class:`Endpoint` IR 对象。
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

        if isinstance(schema, Reference):
            name = _to_pascal_case(schema.ref.rsplit("/", 1)[-1])
            return ResolvedType(type_expr=name, imports=(name,))
        name = f"{_to_pascal_case(endpoint.operation_id)}Response"
        return ResolvedType(type_expr=name, imports=(name,))


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
    file_name: str,
    rendered_code: str,
) -> Path:
    """将渲染后的代码写入文件（文件名由调用方计算，含 ``.py`` 后缀）。

    文件名解析集中在 :func:`_resolve_endpoint_class_and_file`，本函数只
    负责落盘，不再重复 snake_case 派生。

    :param output_dir: 输出目录。
    :param file_name: 目标文件名（含 ``.py`` 后缀）。
    :param rendered_code: 渲染后的 Python 代码。
    :return: 写入的文件路径。
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    file_path = output_path / file_name
    file_path.write_text(rendered_code, encoding="utf-8")
    return file_path
