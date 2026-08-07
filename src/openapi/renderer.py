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
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, Template
from openapi_pydantic import Reference
from pydantic.alias_generators import to_snake

from src.openapi.models import Endpoint, Parameter, RequestBody, Response


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

    def render(self, endpoint: Endpoint) -> tuple[str, str]:
        """渲染 endpoint 的 route.py 内容。

        一并返回从 operationId 派生的文件名（``{snake_case_id}.py``），
        与渲染结果对应——调用方（``make``）拿到 file_name 直接落盘，
        不用再算一次。

        :param endpoint: :class:`Endpoint` IR 对象。
        :return: ``(file_name, rendered_code)`` 元组，``file_name`` 含
            ``.py`` 后缀。
        """
        operation_id = endpoint.operation_id
        class_name = _to_pascal_case(operation_id)
        file_name = f"{to_snake(operation_id)}.py"
        response_type = self._extract_response_info(endpoint.responses, endpoint)
        request_body_type = self._extract_request_body_info(endpoint.request_body, endpoint)
        header_fields, param_fields = self._extract_params(endpoint.parameters)

        imported_models = [t for t in (response_type, request_body_type) if t]

        template: Template = self.env.get_template("endpoint.py.jinja2")
        rendered_code = template.render(
            operation_id=endpoint.operation_id,
            class_name=class_name,
            method=endpoint.method,
            path=endpoint.path,
            summary=endpoint.summary,
            description=endpoint.description,
            response_type=response_type,
            request_body_type=request_body_type,
            header_fields=header_fields,
            param_fields=param_fields,
            imported_models=imported_models,
        )
        return file_name, rendered_code

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
    ) -> str:
        """提取请求体对应的模型名（同时也是要从 ``.models`` 导入的类名）。

        ``$ref`` 路径取末段并 PascalCase 化（对齐 ``datamodel-code-generator``
        对 ``components.schemas`` key 的自动 PascalCase 行为，例如
        ``user-profile`` → ``UserProfile``）；inline object 路径派生为
        ``{PascalOpId}Request``（对齐 ``datamodel-code-generator`` 的
        ``use_operation_id_as_name=True`` —— ``datamodel-code-generator``
        在该模式下对 inline request body 用 ``{operationId}Request`` 命名）。

        :param request_body: :class:`RequestBody` 对象。
        :param endpoint: 当前 :class:`Endpoint` IR 对象。
        :return: 请求体模型名；无 request body / 无 application/json 时返回
            空字符串（无 body 不需要 import）。
        """
        if not request_body:
            return ""

        content = request_body.content or {}
        json_content = content.get("application/json", {})
        schema = getattr(json_content, "media_type_schema", None)

        if isinstance(schema, Reference):
            return _to_pascal_case(schema.ref.rsplit("/", 1)[-1])
        return f"{_to_pascal_case(endpoint.operation_id)}Request"

    def _extract_response_info(
        self,
        responses: dict[str, Response] | None,
        endpoint: Endpoint,
    ) -> str:
        """提取响应对应的模型名（同时也是要从 ``.models`` 导入的类名）。

        ``$ref`` 路径取末段并 PascalCase 化（对齐 ``datamodel-code-generator``
        对 ``components.schemas`` key 的自动 PascalCase 行为，例如
        ``user-profile`` → ``UserProfile``）；inline object 路径派生为
        ``{PascalOpId}Response``（对齐 ``datamodel-code-generator`` 的
        ``use_operation_id_as_name=True`` —— ``datamodel-code-generator``
        在该模式下对 inline response 用 ``{operationId}Response`` 命名）。

        :param responses: OpenAPI 响应字典。
        :param endpoint: 当前 :class:`Endpoint` IR 对象。
        :return: 响应模型名；无 200/201 响应 / 无 application/json 时返回
            空字符串（无响应不需要 import）。
        """
        if not responses:
            return ""

        response_200 = responses.get("200") or responses.get("201")
        if not response_200:
            return ""

        content = response_200.content or {}
        json_content = content.get("application/json")
        if not json_content:
            return ""

        schema = getattr(json_content, "media_type_schema", None)

        if isinstance(schema, Reference):
            return _to_pascal_case(schema.ref.rsplit("/", 1)[-1])
        return f"{_to_pascal_case(endpoint.operation_id)}Response"


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
    """将渲染后的代码写入文件。

    ``file_name`` 由 ``EndpointRenderer.render()`` 一并返回（从
    ``operation_id`` 派生），本函数只负责落盘。

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
