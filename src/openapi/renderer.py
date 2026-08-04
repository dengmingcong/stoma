"""OpenAPI 模板渲染器。

使用 Jinja2 渲染 endpoint 生成模板。
"""

from __future__ import annotations

import keyword
import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, Template
from pydantic.alias_generators import to_snake

from src.openapi.models import Endpoint, Parameter, RequestBody, Response

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


def _get_ref_name(ref: str) -> str:
    """从 $ref 字符串中提取 schema 名称。

    :param ref: $ref 字符串，格式为 #/components/schemas/Name。
    :return: schema 名称。
    """
    return ref.rsplit("/", 1)[-1]


class EndpointRenderer:
    """Endpoint 代码渲染器。"""

    def __init__(
        self,
        components: Any,
        template_path: str | Path | None = None,
    ) -> None:
        """初始化渲染器。

        :param components: openapi_pydantic Components 对象，用于解析 $ref。
        :param template_path: 模板目录路径，默认为 openapi/templates/。
        """
        self.components = components
        if template_path is None:
            template_path = Path(__file__).parent / "templates"
        self.template_dir = Path(template_path)
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, endpoint: Endpoint) -> str:
        """渲染 endpoint 代码。

        :param endpoint: Endpoint IR 对象。
        :return: 渲染后的 Python 代码。
        """
        class_name = operation_id_to_class_name(endpoint.operation_id)
        response_type, response_models = self._extract_response_info(endpoint.responses, class_name)
        request_body_info = self._extract_request_body_info(endpoint.request_body, class_name)
        header_fields, param_fields = self._extract_params(endpoint.parameters)

        template: Template = self.env.get_template("endpoint.py.jinja2")
        return template.render(
            operation_id=endpoint.operation_id,
            class_name=class_name,
            method=endpoint.method,
            path=endpoint.path,
            summary=endpoint.summary,
            description=endpoint.description,
            response_type=response_type,
            response_models=response_models,
            request_body_models=request_body_info["models"],
            request_body_type=request_body_info["type"],
            request_body_embed=request_body_info["embed"],
            request_body_field_name=request_body_info["field_name"] or "body",
            request_body_is_model_ref=request_body_info.get("is_ref", False),
            header_fields=header_fields,
            param_fields=param_fields,
        )

    def _extract_params(self, parameters: list[Parameter]) -> tuple[list[str], list[str]]:
        """提取参数信息。

        :param parameters: 参数列表（openapi_pydantic Parameter 对象）。
        :return: (Header 字段声明列表, Query/Path 字段声明列表)。
        """
        header_fields: list[str] = []
        param_fields: list[str] = []

        for param in parameters:
            name = param.name or ""
            param_in = param.param_in
            # param_in 是 ParameterLocation 枚举。
            location = param_in.value if param_in else "query"
            required = param.required or False
            schema = param.param_schema

            # 将 schema 转为 dict 以便复用已有逻辑。
            schema_dict = schema.model_dump(mode="json") if schema else {}
            json_type = schema_dict.get("type", "Any")
            param_type = map_json_schema_type(str(json_type))

            field_decl = _build_field(name, param_type, required, location)

            if location == "header":
                header_fields.append(field_decl)
            else:
                param_fields.append(field_decl)

        return header_fields, param_fields

    def _extract_request_body_info(
        self,
        request_body: RequestBody | None,
        class_name: str,
    ) -> dict[str, Any]:
        """提取请求体信息。

        检测 embed=True 模式：schema 是 type:object，有且仅有一个 required property。

        :param request_body: openapi_pydantic RequestBody 对象。
        :param class_name: 接口类名，用于生成内联 body 模型名。
        :return: 包含 type、models、embed、field_name 的字典。
        """
        if not request_body:
            return {"type": "", "models": [], "embed": False, "field_name": None}

        content = request_body.content or {}
        json_content = content.get("application/json", {})
        # MediaType 的 media_type_schema 是 Schema | Reference。
        schema = getattr(json_content, "media_type_schema", None)
        if not schema:
            return {"type": "", "models": [], "embed": False, "field_name": None}

        schema_dict = schema.model_dump(mode="json")

        # 检测 embed=True 模式。
        embed, field_name, inner_schema_dict = _detect_embed_wrapper(schema_dict)

        if embed and field_name and inner_schema_dict:
            # 尝试查找内嵌 schema 在 components 中的原始名称。
            inner_title = inner_schema_dict.get("title")
            if inner_title:
                type_name = inner_title
            else:
                inner_name = self._find_schema_name(inner_schema_dict)
                type_name = inner_name or f"{class_name}Request"
            model_code = self._render_object_schema(type_name, inner_schema_dict)
            return {
                "type": type_name,
                "models": [model_code],
                "embed": True,
                "field_name": field_name,
                "is_ref": False,
            }

        # 非 embed：标准处理。
        is_ref = "ref" in schema_dict or "$ref" in schema_dict

        # 如果 schema 有 title（来自 $ref 解析），用 title 生成类。
        schema_title = schema_dict.get("title")
        if schema_title and schema_dict.get("properties"):
            model_code = self._render_object_schema(schema_title, schema_dict)
            return {
                "type": schema_title,
                "models": [model_code],
                "embed": False,
                "field_name": None,
                "is_ref": is_ref,
            }

        # 尝试在 components.schemas 中查找匹配的 schema 名称。
        schema_name = self._find_schema_name(schema_dict)
        if schema_name and schema_dict.get("properties"):
            model_code = self._render_object_schema(schema_name, schema_dict)
            return {
                "type": schema_name,
                "models": [model_code],
                "embed": False,
                "field_name": None,
                "is_ref": is_ref,
            }

        type_name, models = self._resolve_schema_to_type(schema_dict, default_name=f"{class_name}Request")

        # 内联对象需要生成模型类。
        schema_type = schema_dict.get("type", "")
        if schema_type == "object" and not is_ref and "properties" in schema_dict:
            model_code = self._render_object_schema(f"{class_name}Request", schema_dict)
            return {
                "type": f"{class_name}Request",
                "models": [model_code],
                "embed": False,
                "field_name": None,
                "is_ref": False,
            }

        return {
            "type": type_name,
            "models": models,
            "embed": False,
            "field_name": None,
            "is_ref": is_ref,
        }

    def _extract_response_info(
        self, responses: dict[str, Response] | None, class_name: str = ""
    ) -> tuple[str, list[str]]:
        """提取响应信息。

        :param responses: 响应字典（openapi_pydantic Response 对象）。
        :param class_name: 接口类名，用于生成内联响应模型名。
        :return: (响应类型, 内嵌模型列表)。
        """
        if not responses:
            return "", []

        # 查找 200/201 响应。
        response_200 = responses.get("200") or responses.get("201")
        if not response_200:
            return "", []

        content = response_200.content or {}
        json_content = content.get("application/json")
        if not json_content:
            return "", []

        schema = getattr(json_content, "media_type_schema", None)
        if not schema:
            return "", []

        schema_dict = schema.model_dump(mode="json")
        default_name = f"{class_name}Response" if class_name else ""

        # 如果 schema 有 title（来自 $ref 解析），生成以 title 为名的类。
        schema_title = schema_dict.get("title")
        if schema_title and schema_dict.get("properties"):
            model_code = self._render_object_schema(schema_title, schema_dict)
            return schema_title, [model_code]

        # 尝试在 components.schemas 中查找匹配的 schema 名称。
        schema_name = self._find_schema_name(schema_dict)
        if schema_name and schema_dict.get("properties"):
            model_code = self._render_object_schema(schema_name, schema_dict)
            return schema_name, [model_code]

        type_name, models = self._resolve_schema_to_type(schema_dict, default_name)

        # 内联对象需要额外生成模型类。
        schema_type = schema_dict.get("type", "")
        if schema_type == "object" and "properties" in schema_dict and class_name:
            model_code = self._render_object_schema(default_name, schema_dict)
            return default_name, [model_code]
        return type_name, models

    def _resolve_schema_to_type(
        self,
        schema: dict[str, Any],
        default_name: str = "",
    ) -> tuple[str, list[str]]:
        """将 JSON Schema 字典转换为 Python 类型表达式。

        处理 $ref（查 components）、allOf（继承）、oneOf/anyOf（联合类型）。

        :param schema: JSON Schema 字典。
        :param default_name: 内联对象使用的默认模型名。
        :return: (类型表达式, 内嵌模型列表)。
        """
        # 处理 $ref：从 components.schemas 查找并递归解析。
        ref = schema.get("ref") or schema.get("$ref")
        if ref:
            schema_name = _get_ref_name(ref)
            resolved = self._resolve_schema_ref(schema_name)
            if resolved is not None:
                resolved_dict = resolved.model_dump(mode="json")
                return self._resolve_schema_to_type(resolved_dict, schema_name)
            return schema_name, []

        # 处理 oneOf / anyOf：生成联合类型。
        one_of = schema.get("oneOf") or schema.get("anyOf")
        if one_of:
            member_types: list[str] = []
            member_models: list[str] = []
            for item in one_of:
                item_dict = item.model_dump(mode="json") if hasattr(item, "model_dump") else dict(item)
                member_type, models = self._resolve_schema_to_type(item_dict, default_name)
                if member_type:
                    member_types.append(member_type)
                member_models.extend(models)
            union_type = " | ".join(member_types)
            return union_type, member_models

        # 处理 allOf：生成继承类。
        all_of = schema.get("allOf")
        if all_of:
            base_names: list[str] = []
            all_properties: dict[str, Any] = {}
            required_fields: list[str] = []
            all_models: list[str] = []

            for item in all_of:
                item_dict = item.model_dump(mode="json") if hasattr(item, "model_dump") else dict(item)
                item_ref = item_dict.get("ref") or item_dict.get("$ref")
                if item_ref:
                    base_schema_name = _get_ref_name(item_ref)
                    base_names.append(base_schema_name)
                    base_resolved = self._resolve_schema_ref(base_schema_name)
                    if base_resolved:
                        base_dict = base_resolved.model_dump(mode="json")
                        base_props = base_dict.get("properties", {})
                        all_properties.update(base_props)
                        base_required = base_dict.get("required", [])
                        required_fields.extend(base_required)
                        # 递归处理嵌套的 allOf
                        if base_dict.get("allOf"):
                            nested_type, nested_models = self._resolve_schema_to_type(base_dict, base_schema_name)
                            all_models.extend(nested_models)
                else:
                    # 内联 schema
                    item_type, item_models = self._resolve_schema_to_type(item_dict, default_name)
                    all_models.extend(item_models)
                    item_props = item_dict.get("properties", {})
                    all_properties.update(item_props)
                    item_required = item_dict.get("required", [])
                    required_fields.extend(item_required)

            # 渲染当前类的属性
            current_model_code = self._render_object_schema(
                default_name, {"properties": all_properties, "required": required_fields}
            )
            all_models.append(current_model_code)

            # 生成继承类型表达式
            if base_names:
                inherits = ", ".join(base_names)
                return default_name, all_models
            return default_name, all_models

        # 处理 array。
        if schema.get("type") == "array":
            items = schema.get("items") or {}
            items_dict = items.model_dump(mode="json") if hasattr(items, "model_dump") else dict(items)

            # 尝试查找 items schema 在 components 中的原始名称。
            items_name = self._find_schema_name(items_dict)
            if items_name:
                # 查找原始 schema 并生成模型。
                items_schema = self._resolve_schema_ref(items_name)
                if items_schema:
                    schema_dict = items_schema.model_dump(mode="json")
                    model_code = self._render_object_schema(items_name, schema_dict)
                    return f"list[{items_name}]", [model_code]
                return f"list[{items_name}]", []

            items_type, items_models = self._resolve_schema_to_type(items_dict, default_name)
            return f"list[{items_type}]", items_models

        # 处理内联对象。
        if schema.get("type") == "object":
            if "properties" in schema:
                return default_name, []
            return "dict[str, Any]", []

        # 基础类型。
        json_type = schema.get("type", "Any")
        return map_json_schema_type(str(json_type)), []

    def _resolve_schema_ref(self, schema_name: str) -> Any | None:
        """从 components.schemas 解析 schema 引用。

        :param schema_name: schema 名称。
        :return: 解析后的 Schema 对象。
        """
        if not self.components or not self.components.schemas:
            return None
        schemas = self.components.schemas
        if schema_name in schemas:
            return schemas[schema_name]
        return None

    def _find_schema_name(self, schema: dict[str, Any]) -> str | None:
        """在 components.schemas 中查找匹配 schema 内容的名称。

        prance 展开 $ref 后，schema 内容与 components.schemas 中的定义相同，
        通过内容匹配找到原始 schema 名称。

        :param schema: 已展开的 schema 字典（无 $ref）。
        :return: schema 名称，未找到返回 None。
        """
        if not self.components or not self.components.schemas:
            return None
        schemas = self.components.schemas
        if not schemas:
            return None

        # 提取非 None 的关键字段用于匹配。
        match_keys = {"type", "properties", "required", "items", "allOf", "oneOf", "anyOf"}

        def normalize(s: dict[str, Any]) -> dict[str, Any]:
            """去除 None 值，提取关键字段用于匹配。"""
            return {k: v for k, v in s.items() if k in match_keys and v is not None}

        norm_target = normalize(schema)

        for name, schema_obj in schemas.items():
            if hasattr(schema_obj, "model_dump"):
                other = schema_obj.model_dump(mode="json")
            else:
                other = dict(schema_obj)
            if normalize(other) == norm_target:
                return name
        return None

    def _render_object_schema(self, model_name: str, schema: dict[str, Any]) -> str:
        """将内联 object schema 渲染为 Pydantic 模型类定义。

        处理 allOf 继承（父类属性作为基类）。

        :param model_name: 模型类名。
        :param schema: JSON Schema 字典。
        :return: Python 类定义代码字符串。
        """
        all_of = schema.get("allOf")
        if all_of:
            # allOf 处理：从 allOf 中提取父类名列表
            base_names: list[str] = []
            all_properties: dict[str, Any] = {}
            required_fields: list[str] = []

            for item in all_of:
                item_dict = item.model_dump(mode="json") if hasattr(item, "model_dump") else dict(item)
                item_ref = item_dict.get("ref") or item_dict.get("$ref")
                if item_ref:
                    base_name = _get_ref_name(item_ref)
                    base_names.append(base_name)
                    base_resolved = self._resolve_schema_ref(base_name)
                    if base_resolved:
                        base_dict = base_resolved.model_dump(mode="json")
                        all_properties.update(base_dict.get("properties", {}))
                        required_fields.extend(base_dict.get("required", []))
                else:
                    all_properties.update(item_dict.get("properties", {}))
                    required_fields.extend(item_dict.get("required", []))

            # 渲染当前类的属性（只渲染自己新增的属性，不含父类属性）
            own_properties = schema.get("properties", {})
            own_required = schema.get("required", [])
            # 从 all_properties 中去掉 own_properties 的 key，得到只有父类属性的 dict
            parent_props = {k: v for k, v in all_properties.items() if k not in own_properties}

            # 生成父类属性代码（如果有的话）
            parent_model_code = ""
            if parent_props:
                parent_model_code = (
                    self._render_object_schema(
                        f"_{model_name}Base",
                        {"properties": parent_props, "required": [r for r in required_fields if r in parent_props]},
                    )
                    + "\n\n"
                )

            # 生成当前类（只包含自己的属性）
            current_lines = [f"class {model_name}({', '.join(base_names)}):"]
            if not own_properties:
                current_lines.append("    pass")
            else:
                for prop_name, prop_schema in own_properties.items():
                    if not isinstance(prop_schema, dict):
                        continue
                    prop_type, _ = self._resolve_schema_to_type(
                        prop_schema, default_name=f"{model_name}{prop_name.capitalize()}"
                    )
                    required = prop_name in own_required
                    default_str = "" if required else " = None"
                    current_lines.append(f"    {prop_name}: {prop_type}{default_str}")

            return parent_model_code + "\n".join(current_lines)

        # 普通对象
        lines = [f"class {model_name}(BaseModel):"]
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


def _detect_embed_wrapper(schema: dict[str, Any]) -> tuple[bool, str | None, dict[str, Any] | None]:
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


def _build_field(
    name: str,
    param_type: str,
    required: bool,
    location: str,
) -> str:
    """构建字段声明字符串。

    规则：
    - 只有 Header 参数使用 ``Annotated[..., Header()]``
    - 只有不是 snake_case 时才需要 ``Field(serialization_alias=...)``
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
