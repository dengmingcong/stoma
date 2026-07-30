"""OpenAPI 模板渲染器。

使用 Jinja2 渲染 endpoint 生成模板。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

from jinja2 import Environment, FileSystemLoader, Template


class ParameterInfo(TypedDict):
    """OpenAPI 参数信息。"""

    name: str | None
    location: str
    required: bool | None
    schema: dict[str, Any] | None


class HeaderParamInfo(TypedDict):
    """头参数信息。"""

    name: str
    type: str
    required: bool | None
    alias: str


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
        response_type, response_models = self._extract_response_info(responses)
        (
            request_body_models,
            request_body_imports,
        ) = self._extract_request_body_info(request_body)
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
            response_model_imports=[],  # 内嵌模型不需要导入
            request_body_models=request_body_models,
            request_body_model_imports=request_body_imports,
            header_params=header_params,
            param_fields=param_fields,
        )

    def _extract_response_info(
        self, responses: dict[str, Any] | None
    ) -> tuple[str, list[str]]:
        """提取响应信息。

        :param responses: 响应信息。
        :return: (响应类型, 内嵌模型列表)。
        """
        if not responses:
            return "None", []

        # 查找 200 响应。
        response_200 = responses.get("200") or responses.get("201")
        if not response_200:
            return "None", []

        content = response_200.get("content", {})
        json_content = content.get("application/json", {})
        schema = json_content.get("schema")

        if not schema:
            return "None", []

        # 处理 schema。
        if schema.get("type") == "array":
            items = schema.get("items", {})
            ref = items.get("$ref", "")
            if ref:
                model_name = extract_schema_name(ref)
                return f"list[{model_name}]", [f"class {model_name}(BaseModel):\n    pass"]
            return "list[Any]", []

        ref = schema.get("$ref", "")
        if ref:
            model_name = extract_schema_name(ref)
            return model_name, [f"class {model_name}(BaseModel):\n    pass"]

        return "dict[str, Any]", []

    def _extract_request_body_info(
        self, request_body: dict[str, Any] | None
    ) -> tuple[list[str], list[str]]:
        """提取请求体信息。

        :param request_body: 请求体信息。
        :return: (内嵌模型列表, 导入列表)。
        """
        if not request_body:
            return [], []

        content = request_body.get("content", {})
        json_content = content.get("application/json", {})
        schema = json_content.get("schema")

        if not schema:
            return [], []

        ref = schema.get("$ref", "")
        if ref:
            model_name = extract_schema_name(ref)
            return [f"class {model_name}(BaseModel):\n    pass"], []

        # 内联 schema。
        return [], []

    def _extract_params(
        self, parameters: list[ParameterInfo]
    ) -> tuple[list[HeaderParamInfo], list[str]]:
        """提取参数信息。

        :param parameters: 参数列表。
        :return: (头参数列表, 参数字段声明列表)。
        """
        header_params: list[HeaderParamInfo] = []
        param_fields: list[str] = []

        for param in parameters:
            name = param.get("name", "") or ""
            param_location = param.get("location", "") or ""
            required = param.get("required", False) or False
            schema = param.get("schema") or {}
            param_type = schema.get("type", "Any")

            if param_location == "header":
                header_params.append({
                    "name": name,
                    "type": param_type,
                    "required": required,
                    "alias": name,
                })
            else:
                default_str = "" if required else " = None"
                param_fields.append(f"{name}: {param_type}{default_str}")

        return header_params, param_fields


def operation_id_to_class_name(operation_id: str) -> str:
    """将 operationId 转换为类名。

    :param operation_id: operationId 字符串。
    :return: 类名字符串。
    """
    # 保持首字母大写。
    words = operation_id.replace("-", "_").split("_")
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

    :param output_dir: 输出目录。
    :param operation_id: operationId，用于生成文件名。
    :param rendered_code: 渲染后的代码。
    :return: 生成的文件路径。
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    file_name = f"{operation_id}.py"
    file_path = output_path / file_name
    file_path.write_text(rendered_code, encoding="utf-8")
    return file_path
