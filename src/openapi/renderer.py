"""Endpoint 路由文件渲染器。

把 OpenAPI 端点（:class:`src.openapi.models.Endpoint`）渲染成 ``route.py``
文件。**模型类由 ``datamodel-code-generator`` 在前置阶段生成**，本模块
只负责：

- 解析路径 / 查询 / 头部参数并渲染为 Pydantic 字段声明
- 解析请求体引用哪个模型（名字符串）
- 解析响应引用哪个模型（名字符串）
- 渲染 ``Annotated[..., Body(embed=True)]`` 装饰
- 输出 ``from .models import ...`` 导入

所有 schema → model 转换都在 spec pre-process 阶段完成（见
:mod:`src.openapi.spec_transform`），本模块不写 Pydantic 类定义。
"""

from __future__ import annotations

import keyword
import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, Template
from openapi_pydantic.v3.v3_0 import Schema as Schema30
from openapi_pydantic.v3.v3_1 import Schema as Schema31
from pydantic.alias_generators import to_snake

from src.openapi.models import Endpoint, Parameter, RequestBody, Response
from src.openapi.spec_transform import EmbedInfo

Schema = Schema30 | Schema31


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


def _resolve_model_name(schema: Schema, default_name: str) -> str:
    """从 Schema 对象解析出模型名字符串（已经是 ``models.py`` 中将出现的类名）。

    规则：

    - ``$ref`` → 取 ref 末段 schema 名
    - 有 ``title`` → 直接返回（spec pre-process 已经为 inline object 注入 title）
    - inline object（无 title）→ 返回 ``default_name``
    - array → ``list[<items_model_name>]``
    - 标量 → ``dict[str, Any]``（无法建模）
    """
    if schema.title:
        return schema.title
    if schema.type == "array" and schema.items is not None and isinstance(schema.items, Schema):
        items_name = schema.items.title if schema.items.title else default_name
        return f"list[{items_name}]"
    if schema.type == "object" and not schema.properties:
        return "dict[str, Any]"
    return default_name


def _unwrap_model_name(type_expr: str) -> str:
    """从类型表达式（如 ``list[User]``、``User``）提取需要 import 的模型名。

    - ``User`` → ``User``
    - ``list[User]`` → ``User``
    - ``dict[str, Any]`` → 空字符串（不导入）
    - ``""`` → 空字符串
    """
    if not type_expr:
        return ""
    if type_expr.startswith("list[") and type_expr.endswith("]"):
        return type_expr[5:-1]
    return type_expr


class EndpointRenderer:
    """Endpoint 路由文件渲染器。"""

    def __init__(
        self,
        template_path: str | Path | None = None,
        embed_infos: dict[str, EmbedInfo] | None = None,
    ) -> None:
        """初始化渲染器。

        :param template_path: 模板目录路径，默认为 ``openapi/templates/``。
        :param embed_infos: 按 ``operation_id`` 索引的 embed wrapper 信息。
            用于在 ``route.py`` 中渲染 ``Body(embed=True)`` 并使用 wrapper
            字段名作为接口类字段名。
        """
        if template_path is None:
            template_path = Path(__file__).parent / "templates"
        self.template_dir = Path(template_path)
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.embed_infos: dict[str, EmbedInfo] = embed_infos or {}

    def render(self, endpoint: Endpoint) -> str:
        """渲染 endpoint 的 route.py 内容。

        :param endpoint: :class:`Endpoint` IR 对象。
        :return: 渲染后的 Python 源码字符串。
        """
        class_name = _to_pascal_case(endpoint.operation_id)
        response_type, response_imports = self._extract_response_info(endpoint.responses, class_name)
        request_body_info = self._extract_request_body_info(endpoint.request_body, class_name, endpoint.operation_id)
        header_fields, param_fields = self._extract_params(endpoint.parameters)

        imported_models: list[str] = []
        if response_type and response_type != "dict[str, Any]":
            imported_models.append(_unwrap_model_name(response_type))
        if request_body_info["type"]:
            imported_models.append(_unwrap_model_name(request_body_info["type"]))
        imported_models = [m for m in imported_models if m]

        template: Template = self.env.get_template("endpoint.py.jinja2")
        return template.render(
            operation_id=endpoint.operation_id,
            class_name=class_name,
            method=endpoint.method,
            path=endpoint.path,
            summary=endpoint.summary,
            description=endpoint.description,
            response_type=response_type,
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
        operation_id: str,
    ) -> dict[str, Any]:
        """提取请求体信息。

        行为：

        - 引用 ``components.schemas`` 或有 ``title`` 的 schema → ``type`` 等于
          schema 名（``models.py`` 中已有同名类）。
        - embed wrapper（已由 :func:`unwrap_embed_wrappers` 在 spec 预处理
          阶段解开）→ 通过 ``self.embed_infos[operation_id]`` 拿 wrapper
          字段名，渲染 ``Body(embed=True)``。
        - 未匹配 → ``type`` 为空字符串（不生成 body 字段）。

        :param request_body: :class:`RequestBody` 对象。
        :param class_name: 接口类名，做 fallback。
        :param operation_id: 用于查找 embed_info。
        :return: ``{"type": str, "embed": bool, "field_name": str | None}``。
        """
        if not request_body:
            return {"type": "", "embed": False, "field_name": None}

        embed_info = self.embed_infos.get(operation_id)
        content = request_body.content or {}
        json_content = content.get("application/json", {})
        schema = getattr(json_content, "media_type_schema", None)
        if not isinstance(schema, Schema):
            return {"type": "", "embed": False, "field_name": None}

        default_name = embed_info.model_name if embed_info else f"{class_name}Request"
        type_name = _resolve_model_name(schema, default_name)

        if embed_info:
            return {
                "type": type_name,
                "embed": True,
                "field_name": embed_info.field_name,
            }
        return {"type": type_name, "embed": False, "field_name": None}

    def _extract_response_info(
        self,
        responses: dict[str, Response] | None,
        class_name: str,
    ) -> tuple[str, list[str]]:
        """提取响应信息（类名引用 + 需导入的模型名列表）。

        :param responses: OpenAPI 响应字典。
        :param class_name: 接口类名，做 fallback。
        :return: ``(响应类型字符串, 需导入的模型名列表)``。
        """
        if not responses:
            return "", []

        response_200 = responses.get("200") or responses.get("201")
        if not response_200:
            return "", []

        content = response_200.content or {}
        json_content = content.get("application/json")
        if not json_content:
            return "", []

        schema = getattr(json_content, "media_type_schema", None)
        if not isinstance(schema, Schema):
            return "", []

        default_name = f"{class_name}Response" if class_name else ""
        type_name = _resolve_model_name(schema, default_name)
        return type_name, [type_name] if type_name else []


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
