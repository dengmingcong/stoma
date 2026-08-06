"""OpenAPI 规范解析器。

使用 openapi-pydantic 解析 OpenAPI Specification 文件，
提取路径、方法、参数、schema 等信息，供代码生成器使用。
"""

import json
import re
from pathlib import Path
from typing import Any

import yaml
from openapi_pydantic import OpenAPI
from openapi_pydantic.v3.v3_0 import OpenAPI as OpenAPI30
from openapi_pydantic.v3.v3_0 import Operation as Operation30
from openapi_pydantic.v3.v3_1 import Operation as Operation31
from prance import ResolvingParser

from src.openapi.models import Endpoint

Operation = Operation30 | Operation31


def _operation_id_to_pascal(operation_id: str) -> str:
    """把 operationId 转为 PascalCase 类名。

    支持 snake_case、camelCase、PascalCase 和含连字符四种格式。

    :param operation_id: 原始 operationId。
    :return: PascalCase 类名。
    """
    normalized = operation_id.replace("-", "_")
    words = re.split(r"[_-]+|(?<=[a-z0-9])(?=[A-Z])", normalized)
    return "".join(word.capitalize() for word in words if word)


def _is_inline_object(schema: dict[str, Any]) -> bool:
    """检测 schema 是否是需要注入 title 的「内联 object」。

    - ``$ref`` schema 不算（datamodel-codegen 自己会从 ref 末段取名）
    - 已有 ``title`` 不算（避免覆盖 $ref 解析后已带 title 的 schema）
    - 必须 ``type: object`` 且 ``properties`` 非空

    :param schema: 必须是 dict（调用方应先 ``isinstance(x, dict)`` 判断）。
    """
    if "$ref" in schema:
        return False
    if schema.get("title"):
        return False
    if schema.get("type") != "object":
        return False
    properties = schema.get("properties")
    return isinstance(properties, dict) and len(properties) > 0


def _fill_schema_titles(raw_spec_dict: dict[str, Any]) -> bool:
    """为所有 schema 注入 title，返回是否在 paths 中找到任何 payload。

    在 prance 展开之前调用：

    1. ``components.schemas.X`` → ``title = X``（让 prance 复制时保留 title，
       datamodel-codegen 跨 components + paths 做去重）
    2. ``paths[*][*].requestBody.content["application/json"].schema``（inline）
       → ``title = {OperationId}Request``
    3. ``paths[*][*].responses[200/201].content["application/json"].schema``
       → ``title = {OperationId}Response``

    **不**做 embed wrapper 检测。OpenAPI 单属性 wrapper（如
    ``{data: User}``）让 datamodel-codegen 直接按 wrapper 形态生成
    ``class CreateXRequest { data: User }``，runtime 用 ``body: CreateXRequest``
    直接发——body 形态由 spec 自然决定，不做猜测。

    已带 title 的 schema 跳过，避免覆盖正确的类名。

    :param raw_spec_dict: OpenAPI 规范字典（修改入参——prance 展开后 title 仍在）。
    :return: 是否在 paths 中找到任何 ``application/json`` 的 request body 或
        200/201 响应。cli 据此判断是否要生成 ``models.py``。
    """
    # Pass 1：components.schemas.X → title = X
    components_schemas = raw_spec_dict.get("components", {}).get("schemas", {})
    if isinstance(components_schemas, dict):
        for name, json_media_type_schema in components_schemas.items():
            if isinstance(json_media_type_schema, dict) and not json_media_type_schema.get("title"):
                json_media_type_schema["title"] = name

    # Pass 2 / 3：paths[*][*] 的 inline object 注入 title
    has_payload = False
    paths = raw_spec_dict.get("paths", {})
    if not isinstance(paths, dict):
        return False
    for path_item in paths.values():
        if not isinstance(path_item, dict):
            continue
        for _method, op in path_item.items():
            if not isinstance(op, dict):
                continue
            operation_id = op.get("operationId")
            if not isinstance(operation_id, str) or not operation_id:
                continue
            pascal = _operation_id_to_pascal(operation_id)

            # 请求体
            rb = op.get("requestBody")
            if isinstance(rb, dict):
                content = rb.get("content", {})
                json_media_type_obj = content.get("application/json", {})
                if isinstance(json_media_type_obj, dict):
                    json_media_type_schema = json_media_type_obj.get("schema")
                    if isinstance(json_media_type_schema, dict) and _is_inline_object(json_media_type_schema):
                        json_media_type_schema["title"] = f"{pascal}Request"
                        has_payload = True

            # 响应 200/201
            responses = op.get("responses", {})
            if isinstance(responses, dict):
                for status in ("200", "201"):
                    resp = responses.get(status)
                    if not isinstance(resp, dict):
                        continue
                    content = resp.get("content", {})
                    json_media_type_obj = content.get("application/json", {})
                    if isinstance(json_media_type_obj, dict):
                        json_media_type_schema = json_media_type_obj.get("schema")
                        if isinstance(json_media_type_schema, dict) and _is_inline_object(json_media_type_schema):
                            json_media_type_schema["title"] = f"{pascal}Response"
                            has_payload = True

    return has_payload


class OpenAPISchemaError(Exception):
    """OpenAPI schema 校验失败。"""

    pass


class OpenAPIParser:
    """OpenAPI 规范解析器。

    使用 openapi-pydantic 解析 OpenAPI Specification 文件，
    提取路径、方法、参数、schema 等信息，供代码生成器使用。

    :var spec_path: OpenAPI 规范文件的路径。
    :vartype spec_path: Path
    """

    def __init__(self, spec_path: str | Path) -> None:
        """初始化解析器。

        :param spec_path: OpenAPI 规范文件路径（支持 YAML 或 JSON）。
        """
        self.spec_path = Path(spec_path)
        self._spec_dict: dict[str, Any] | None = None
        self._spec: OpenAPI | OpenAPI30 | None = None
        self._has_payloads: bool = False

    @property
    def has_payloads(self) -> bool:
        """``load()`` 后：paths 中是否找到任何 request body 或 200/201 响应的 ``application/json``。

        由 :func:`_fill_schema_titles` 在遍历 paths 时设置，避免 cli 重复 walk。
        """
        return self._has_payloads

    def load(self) -> None:
        """加载 OpenAPI 规范文件，并展开所有内部 $ref。

        使用 prance 解析，自动处理 YAML 和 JSON 格式，
        并将所有 $ref 引用解析为实际对象。

        :raise FileNotFoundError: 规范文件不存在。
        :raise ValueError: 解析失败。
        """
        if not self.spec_path.exists():
            msg = f"OpenAPI specification file not found: {self.spec_path}"
            raise FileNotFoundError(msg)

        content = self.spec_path.read_text(encoding="utf-8")

        suffix = self.spec_path.suffix.lower()
        if suffix in {".yaml", ".yml"}:
            raw_spec_dict = yaml.safe_load(content)
        elif suffix == ".json":
            raw_spec_dict = json.loads(content)
        else:
            msg = f"Unsupported file suffix: {suffix}. Supported: .yaml, .yml, .json"
            raise ValueError(msg)

        # 先检查版本，不支持则提前报错。
        openapi_version = raw_spec_dict.get("openapi", "") if isinstance(raw_spec_dict, dict) else ""
        if not openapi_version.startswith(("3.0.", "3.1.")):
            msg = f"Unsupported OpenAPI version: {openapi_version}. Only 3.0.x and 3.1.x are supported."
            raise ValueError(msg)

        # 给 components.schemas 补全 title，让 prance 展开后的内联副本
        # 也带 title；这是 datamodel-codegen 跨 components 和 paths 做
        # 去重时的关键标识（仅靠 dict key 不够，必须 title 也一致）。
        self._has_payloads = _fill_schema_titles(raw_spec_dict)

        try:
            modified_content = yaml.dump(raw_spec_dict) if suffix in {".yaml", ".yml"} else json.dumps(raw_spec_dict)
            parser = ResolvingParser(spec_string=modified_content, validation=False)
            parser.parse()
            self._spec_dict = parser.specification
        except Exception as e:
            raise ValueError(f"Failed to parse OpenAPI specification: {e}") from e

    def validate(self) -> None:
        """使用 openapi-pydantic 校验 OpenAPI 规范。

        :raise OpenAPISchemaError: 规范不符合 OpenAPI Schema。
        :raise ValueError: 尚未加载规范。
        """
        if self._spec_dict is None:
            msg = "OpenAPI specification not loaded. Call load() first."
            raise ValueError(msg)

        try:
            openapi_version = self.get_openapi_version()
            if openapi_version.startswith("3.1."):
                self._spec = OpenAPI.model_validate(self._spec_dict)
            elif openapi_version.startswith("3.0."):
                self._spec = OpenAPI30.model_validate(self._spec_dict)
            else:
                msg = f"Unsupported OpenAPI version: {openapi_version}. Only 3.0.x and 3.1.x are supported."
                raise OpenAPISchemaError(msg)
        except OpenAPISchemaError:
            raise
        except Exception as e:
            msg = f"OpenAPI specification validation failed: {e}"
            raise OpenAPISchemaError(msg) from e

    @property
    def spec(self) -> OpenAPI | OpenAPI30:
        """获取已解析的 OpenAPI 规范对象。

        :return: OpenAPI 规范 Pydantic 模型。
        :raise RuntimeError: 尚未调用 validate() 方法。
        """
        if self._spec is None:
            msg = "OpenAPI specification not validated. Call validate() first."
            raise RuntimeError(msg)
        return self._spec

    def get_openapi_version(self) -> str:
        """获取 OpenAPI 版本。

        :return: OpenAPI 版本号（如 "3.0.0"、"3.1.0"）。
        """
        return self._spec_dict.get("openapi", "") if self._spec_dict else ""

    def get_endpoints(self) -> list[Endpoint]:
        """获取所有 endpoint 的结构化信息。

        prance 已在 load() 阶段展开所有 $ref，此处直接取值。

        :return: endpoint 列表。
        :raise RuntimeError: 尚未验证规范。
        """
        if self._spec is None:
            msg = "OpenAPI specification not validated. Call validate() first."
            raise RuntimeError(msg)

        endpoints: list[Endpoint] = []
        paths = self._spec.paths
        if not paths:
            return endpoints

        for path, path_item in paths.items():
            method_to_operation = {
                method: operation
                for method in ("get", "post", "put", "patch", "delete")
                if (operation := getattr(path_item, method))
            }
            operation: Operation
            for method, operation in method_to_operation.items():
                endpoint = Endpoint(
                    operation_id=operation.operationId or "",
                    method=method,
                    path=path,
                    summary=operation.summary,
                    description=operation.description,
                    parameters=operation.parameters or [],
                    request_body=operation.requestBody,
                    responses=operation.responses,
                )
                endpoints.append(endpoint)

        return endpoints
