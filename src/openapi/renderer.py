"""OpenAPI 模板渲染器。

使用 Jinja2 渲染 endpoint 生成模板。
"""

from __future__ import annotations

import keyword
import re
from pathlib import Path
from typing import Any, TypedDict

from jinja2 import Environment, FileSystemLoader, Template
from pydantic.alias_generators import to_snake


class ParameterInfo(TypedDict):
    """OpenAPI 参数信息。"""

    name: str | None
    location: str
    required: bool | None
    schema: dict[str, Any] | None


class RequestBodyInfo(TypedDict):
    """请求体信息（包含 embed 标记）。"""

    type: str
    models: list[str]
    embed: bool
    field_name: str | None
    is_model_ref: bool


_JSON_SCHEMA_TYPE_TO_PYTHON: dict[str, str] = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "array": "list",
    "object": "dict",
}


def map_json_schema_type(json_type: str) -> str:
    """将 JSON Schema 类型映射为 Python 类型。

    :param json_type: JSON Schema 类型（如 "string"、"integer"）。
    :return: Python 类型字符串。
    """
    return _JSON_SCHEMA_TYPE_TO_PYTHON.get(json_type, json_type)


def _is_snake_case(name: str) -> bool:
    """检测 name 是否已经是合法的 snake_case（且不是 Python 关键字）。

    :param name: 候选名字。
    :return: 是否为合法 snake_case。
    """
    if not name:
        return False
    if keyword.iskeyword(name):
        return False
    return bool(re.fullmatch(r"[a-z][a-z0-9_]*", name))


def _to_field_name(name: str) -> str:
    """将 OpenAPI 参数名转为合法的 snake_case field 名。

    注意：仅在非 snake_case 时调用。

    :param name: 原始 OpenAPI 参数名。
    :return: 合法的 snake_case field 名。
    """
    # 非字母数字字符（含 - 和 .）统一替换为下划线
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_") or "param"

    if cleaned[0].isdigit():
        cleaned = f"n_{cleaned}"

    if keyword.iskeyword(cleaned):
        cleaned = f"p_{cleaned}"

    return to_snake(cleaned)


def _build_field(
    name: str,
    param_type: str,
    required: bool,
    location: str,
) -> str:
    """构建字段声明字符串。

    规则：
    - 只有 Header 参数使用 ``Annotated[..., Header()]``
    - 只有不是 snake_case 时才需要 ``Field(alias=...)``
    - 只有非 required 才需要 ``| None``

    :param name: 原始 OpenAPI 参数名。
    :param param_type: Python 类型字符串。
    :param required: 是否必需。
    :param location: 参数位置（"header" 或 "query"/"path"）。
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


class EndpointRenderer:
    """Endpoint 代码渲染器。"""

    def __init__(self, template_path: str | Path | None = None) -> None:
        """初始化渲染器。

        :param template_path: 模板目录路径，默认为 openapi/templates/。
        """
        if template_path is None:
            template_path = Path(__file__).parent / "templates"
        self.template_dir = Path(template_path)
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(
        self,
        operation_id: str,
        method: str,
        path: str,
        parameters: list[ParameterInfo],
        request_body: dict[str, Any] | None,
        responses: dict[str, Any] | None,
        summary: str | None = None,
        description: str | None = None,
    ) -> str:
        """渲染 endpoint 代码。

        :param operation_id: operationId。
        :param method: HTTP 方法。
        :param path: API 路径。
        :param parameters: 参数列表。
        :param request_body: 请求体信息。
        :param responses: 响应信息。
        :param summary: 摘要。
        :param description: 描述。
        :return: 渲染后的 Python 代码。
        """
        class_name = operation_id_to_class_name(operation_id)
        response_type, response_models = self._extract_response_info(responses, class_name)
        request_body_info = self._extract_request_body_info(request_body, class_name)
        header_params, param_fields = self._extract_params(parameters)

        template: Template = self.env.get_template("endpoint.py.jinja2")
        return template.render(
            operation_id=operation_id,
            class_name=class_name,
            method=method,
            path=path,
            summary=summary,
            description=description,
            response_type=response_type,
            response_models=response_models,
            response_model_imports=[],
            request_body_models=request_body_info["models"],
            request_body_model_imports=[],
            request_body_type=request_body_info["type"],
            request_body_embed=request_body_info["embed"],
            request_body_field_name=request_body_info["field_name"] or "body",
            request_body_is_model_ref=request_body_info["is_model_ref"],
            header_fields=header_params,
            param_fields=param_fields,
        )

    def _extract_response_info(
        self, responses: dict[str, Any] | None, class_name: str = ""
    ) -> tuple[str, list[str]]:
        """提取响应信息。

        :param responses: 响应信息。
        :param class_name: 接口类名，用于生成内联响应模型名。
        :return: (响应类型, 内嵌模型列表)。
        """
        if not responses:
            return "", []

        # 查找 200/201 响应。
        response_200 = responses.get("200") or responses.get("201")
        if not response_200:
            return "", []

        content = response_200.get("content") or {}
        json_content = content.get("application/json", {})
        schema = json_content.get("schema")

        if not schema:
            return "", []

        default_name = f"{class_name}Response" if class_name else ""
        type_name, models = self._resolve_schema_to_type(schema, default_name)
        # 内联对象（无 $ref）需要额外生成模型类。
        if (
            schema.get("type") == "object"
            and "$ref" not in schema
            and "properties" in schema
            and class_name
        ):
            model_code = self._render_object_schema(default_name, schema)
            return default_name, [model_code]
        return type_name, models

    def _extract_request_body_info(
        self,
        request_body: dict[str, Any] | None,
        class_name: str,
    ) -> RequestBodyInfo:
        """提取请求体信息。

        检测 embed=True 模式：schema 是 type:object，有且仅有一个 required property。

        生成逻辑与请求体示例：

        | 场景 | OpenAPI schema | 生成代码 | 请求体示例 |
        |------|----------------|----------|------------|
        | 直接 $ref | ``{$ref: User}`` | ``body: User`` | ``{"id": "1"}`` |
        | 内联 object | ``{type: object, properties: {...}}`` | ``body: Annotated[Req, Body()]`` | ``{"name": "Bob"}`` |
        | 数组 | ``{type: array, items: {$ref: Item}}`` | ``body: Annotated[list[Item], Body()]`` | ``[{"id": "1"}]`` |
        | 标量 | ``{type: integer}`` | ``body: Annotated[int, Body()]`` | ``42`` |
        | embed=True | 单属性 wrapper object | ``data: Annotated[User, Body(embed=True)]`` | ``{"data": {"id": "1"}}`` |

        :param request_body: 请求体信息。
        :param class_name: 接口类名，用于生成内联 body 模型名。
        :return: RequestBodyInfo，包含类型、内嵌模型、embed 标记和字段名。
        """
        if not request_body:
            return RequestBodyInfo(type="", models=[], embed=False, field_name=None, is_model_ref=False)

        content = request_body.get("content") or {}
        json_content = content.get("application/json", {})
        schema = json_content.get("schema")

        if not schema:
            return RequestBodyInfo(type="", models=[], embed=False, field_name=None, is_model_ref=False)

        # 检测 embed=True 模式。
        embed, field_name, inner_schema = self._detect_embed_wrapper(schema)

        if embed and field_name and inner_schema:
            # embed=True：处理内嵌的 schema。
            type_name, models = self._resolve_schema_to_type(
                inner_schema, default_name=f"{class_name}Request"
            )
            is_model_ref = "$ref" in inner_schema
            return RequestBodyInfo(
                type=type_name,
                models=models,
                embed=True,
                field_name=field_name,
                is_model_ref=is_model_ref,
            )

        # 非 embed：标准处理。
        type_name, models = self._resolve_schema_to_type(
            schema, default_name=f"{class_name}Request"
        )
        is_model_ref = "$ref" in schema

        # 如果是 inline 对象（没有 $ref），需要生成模型类。
        if schema.get("type") == "object" and not is_model_ref:
            model_code = self._render_object_schema(
                f"{class_name}Request", schema
            )
            return RequestBodyInfo(
                type=f"{class_name}Request",
                models=[model_code],
                embed=False,
                field_name=None,
                is_model_ref=False,
            )

        return RequestBodyInfo(
            type=type_name,
            models=models,
            embed=False,
            field_name=None,
            is_model_ref=is_model_ref,
        )

    def _detect_embed_wrapper(
        self, schema: dict[str, Any]
    ) -> tuple[bool, str | None, dict[str, Any] | None]:
        """检测是否是 embed=True 的单属性 wrapper。

        embed=True 的 OpenAPI 特征：
        - type: object
        - 有且仅有一个 property
        - 该 property 的 key 在 required 列表中

        :param schema: JSON Schema 字典。
        :return: (is_embed, field_name, inner_schema)。
        """
        if schema.get("type") != "object":
            return False, None, None

        properties = schema.get("properties") or {}
        if len(properties) != 1:
            return False, None, None

        required = schema.get("required") or []
        field_name = list(properties.keys())[0]

        if field_name not in required:
            return False, None, None

        inner_schema = properties[field_name]
        if not isinstance(inner_schema, dict):
            return False, None, None

        return True, field_name, inner_schema

    def _resolve_schema_to_type(
        self,
        schema: dict[str, Any],
        default_name: str = "",
    ) -> tuple[str, list[str]]:
        """将 JSON Schema 转换为 Python 类型表达式。

        :param schema: JSON Schema 字典。
        :param default_name: 内联对象使用的默认模型名。
        :return: (类型表达式, 内嵌模型列表)。
        """
        # $ref 引用。
        ref = schema.get("$ref")
        if ref:
            model_name = extract_schema_name(ref)
            return model_name, [f"class {model_name}(BaseModel):\n    pass"]

        # 数组类型。
        if schema.get("type") == "array":
            items = schema.get("items") or {}
            items_type, items_models = self._resolve_schema_to_type(items, default_name)
            return f"list[{items_type}]", items_models

        # 内联对象。
        if schema.get("type") == "object":
            # 对象有 properties 才视为有意义的模型。
            if "properties" in schema:
                return default_name, []
            return "dict[str, Any]", []

        # 基础类型。
        json_type = schema.get("type", "Any")
        return map_json_schema_type(str(json_type)), []

    def _render_object_schema(
        self, model_name: str, schema: dict[str, Any]
    ) -> str:
        """将内联 object schema 渲染为 Pydantic 模型类定义。

        :param model_name: 模型类名。
        :param schema: JSON Schema 字典。
        :return: Python 类定义代码字符串。
        """
        lines: list[str] = [f"class {model_name}(BaseModel):"]
        properties = schema.get("properties") or {}
        required_list = schema.get("required") or []

        if not properties:
            lines.append("    pass")
            return "\n".join(lines)

        for prop_name, prop_schema in properties.items():
            if not isinstance(prop_schema, dict):
                continue
            prop_type, _ = self._resolve_schema_to_type(
                prop_schema, default_name=f"{model_name}{prop_name.capitalize()}"
            )
            required = prop_name in required_list
            default_str = "" if required else " = None"
            lines.append(f"    {prop_name}: {prop_type}{default_str}")

        return "\n".join(lines)

    def _extract_params(
        self, parameters: list[ParameterInfo]
    ) -> tuple[list[str], list[str]]:
        """提取参数信息。

        :param parameters: 参数列表。
        :return: (Header 字段声明列表, Query/Path 字段声明列表)。
        """
        header_fields: list[str] = []
        param_fields: list[str] = []

        for param in parameters:
            name = param.get("name", "")
            param_location = param.get("location", "")
            required = param.get("required", False)
            schema = param.get("schema") or {}
            json_type = schema.get("type", "Any")
            param_type = map_json_schema_type(str(json_type))

            field_decl = _build_field(name, param_type, required, param_location)

            if param_location == "header":
                header_fields.append(field_decl)
            else:
                param_fields.append(field_decl)

        return header_fields, param_fields


def operation_id_to_class_name(operation_id: str) -> str:
    """将 operationId 转换为类名。

    支持 snake_case（list_users）和 camelCase（listUsers）两种格式。

    :param operation_id: operationId 字符串。
    :return: 类名字符串。
    """
    return _to_pascal_case(operation_id)


def operation_id_to_snake_case(operation_id: str) -> str:
    """将 operationId 转换为 snake_case。

    支持 snake_case（list_users）和 camelCase（listUsers）两种格式。

    :param operation_id: operationId 字符串。
    :return: snake_case 字符串。
    """
    # 统一分隔符：连字符转下划线。
    normalized = operation_id.replace("-", "_")
    # 在小写字母/数字与大写字母之间插入下划线（处理 camelCase）。
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", normalized).split("_")
    return "_".join(word.lower() for word in words if word)


def _to_pascal_case(operation_id: str) -> str:
    """将 operationId 转换为 PascalCase。

    :param operation_id: operationId 字符串。
    :return: PascalCase 字符串。
    """
    normalized = operation_id.replace("-", "_")
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", normalized).split("_")
    return "".join(word.capitalize() for word in words if word)


def extract_schema_name(ref: str) -> str:
    """从 $ref 中提取 schema 名称。

    :param ref: $ref 字符串，格式为 #/components/schemas/Name。
    :return: schema 名称。
    """
    if not ref.startswith("#/components/schemas/"):
        msg = f"Unsupported $ref format: {ref}"
        raise ValueError(msg)
    return ref.split("/")[-1]


def render_to_file(
    output_dir: str | Path,
    operation_id: str,
    rendered_code: str,
) -> Path:
    """将渲染后的代码写入文件。

    文件名基于 operationId 转换为 snake_case（如 listUsers → list_users.py）。

    :param output_dir: 输出目录。
    :param operation_id: operationId，用于生成文件名。
    :param rendered_code: 渲染后的代码。
    :return: 生成的文件路径。
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    file_name = f"{operation_id_to_snake_case(operation_id)}.py"
    file_path = output_path / file_name
    file_path.write_text(rendered_code, encoding="utf-8")
    return file_path
