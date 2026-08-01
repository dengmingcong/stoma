"""OpenAPI 规范解析器。

使用 openapi-pydantic 解析 OpenAPI Specification 文件，
提取路径、方法、参数、schema 等信息，供代码生成器使用。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from openapi_pydantic import OpenAPI
from openapi_pydantic.v3.v3_0 import (
    OpenAPI as OpenAPI30,
)
from openapi_pydantic.v3.v3_0 import (
    Operation as Operation30,
)
from openapi_pydantic.v3.v3_0 import (
    Parameter as Parameter30,
)
from openapi_pydantic.v3.v3_0 import (
    ParameterLocation as ParameterLocation30,
)
from openapi_pydantic.v3.v3_0 import (
    Reference as Reference30,
)
from openapi_pydantic.v3.v3_0 import (
    RequestBody as RequestBody30,
)
from openapi_pydantic.v3.v3_0 import (
    Response as Response30,
)
from openapi_pydantic.v3.v3_1 import (
    Operation as Operation31,
)
from openapi_pydantic.v3.v3_1 import (
    Parameter as Parameter31,
)
from openapi_pydantic.v3.v3_1 import (
    ParameterLocation as ParameterLocation31,
)
from openapi_pydantic.v3.v3_1 import (
    Reference as Reference31,
)
from openapi_pydantic.v3.v3_1 import (
    RequestBody as RequestBody31,
)
from openapi_pydantic.v3.v3_1 import (
    Response as Response31,
)

Operation = Operation30 | Operation31
Parameter = Parameter30 | Parameter31
ParameterLocation = ParameterLocation30 | ParameterLocation31
Reference = Reference30 | Reference31
RequestBody = RequestBody30 | RequestBody31
Response = Response30 | Response31


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

    def load(self) -> dict[str, Any]:
        """加载 OpenAPI 规范文件。

        根据文件后缀判断格式：

        - ``.yaml`` / ``.yml`` → YAML 格式
        - ``.json`` → JSON 格式

        :return: 加载后的 OpenAPI 规范字典。
        :raise FileNotFoundError: 规范文件不存在。
        :raise ValueError: 不支持的文件后缀。
        """
        if not self.spec_path.exists():
            msg = f"OpenAPI specification file not found: {self.spec_path}"
            raise FileNotFoundError(msg)

        content = self.spec_path.read_text(encoding="utf-8")

        suffix = self.spec_path.suffix.lower()
        if suffix in {".yaml", ".yml"}:
            self._spec_dict = yaml.safe_load(content)
        elif suffix == ".json":
            self._spec_dict = json.loads(content)
        else:
            msg = f"Unsupported file suffix: {suffix}. Supported: .yaml, .yml, .json"
            raise ValueError(msg)

        if not isinstance(self._spec_dict, dict):
            msg = "OpenAPI specification must be a JSON object."
            raise ValueError(msg)

        return self._spec_dict

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

    def get_endpoints(self) -> list[dict[str, Any]]:
        """获取所有 endpoint 的结构化信息。

        每个 endpoint 包含 path、method、operation_id、summary、
        parameters、request_body、responses、tags。

        :return: endpoint 列表。
        :raise RuntimeError: 尚未验证规范。
        """
        if self._spec is None:
            msg = "OpenAPI specification not validated. Call validate() first."
            raise RuntimeError(msg)

        endpoints: list[dict[str, Any]] = []
        paths = self._spec.paths
        if not paths:
            return endpoints

        for path, path_item in paths.items():
            for method in ["get", "post", "put", "patch", "delete"]:
                operation = getattr(path_item, method, None)
                if operation is None:
                    continue

                params = self._extract_parameters(operation)
                endpoint: dict[str, Any] = {
                    "path": path,
                    "method": method,
                    "operation_id": operation.operationId,
                    "summary": operation.summary,
                    "description": operation.description,
                    "parameters": params,
                    "request_body": self._extract_request_body(operation),
                    "responses": self._extract_responses(operation),
                    "tags": operation.tags or [],
                }
                endpoints.append(endpoint)

        return endpoints

    def _extract_parameters(self, operation: Operation) -> list[dict[str, Any]]:
        """提取操作参数。

        :param operation: OpenAPI 操作对象。
        :return: 参数列表。
        """
        if not operation.parameters:
            return []

        params: list[dict[str, Any]] = []
        for p in operation.parameters:
            # 跳过 Reference 类型（Reference 只有 $ref，没有 param_in 等字段）。
            if isinstance(p, Reference):
                continue
            if not isinstance(p, Parameter):
                continue

            param_in = p.param_in
            if isinstance(param_in, ParameterLocation):
                param_in = param_in.value

            schema_obj = p.param_schema
            schema: dict[str, Any] | None = None
            if schema_obj is not None:
                schema = schema_obj.model_dump(mode="json")

            params.append(
                {
                    "name": p.name,
                    "location": param_in,
                    "required": p.required,
                    "schema": schema,
                }
            )
        return params

    def _extract_request_body(self, operation: Operation) -> dict[str, Any] | None:
        """提取请求体信息。

        :param operation: OpenAPI 操作对象。
        :return: 请求体信息。
        """
        if not operation.requestBody:
            return None

        rb = operation.requestBody
        if isinstance(rb, Reference):
            return {"$ref": rb.ref}
        if isinstance(rb, RequestBody):
            dumped = rb.model_dump(mode="json")
        else:
            dumped = dict(rb)
        # 规范化内嵌的 MediaType 结构。
        content = dumped.get("content")
        if isinstance(content, dict):
            for media_type in content.values():
                self._normalize_media_type(media_type)
        return dumped

    def _extract_responses(self, operation: Operation) -> dict[str, Any] | None:
        """提取响应信息。

        :param operation: OpenAPI 操作对象。
        :return: 响应信息。
        """
        if not operation.responses:
            return None

        # Responses 是 Dict[str, Response]，递归转换为 dict。
        result: dict[str, Any] = {}
        for status_code, response in operation.responses.items():
            if isinstance(response, Response):
                result[status_code] = response.model_dump(mode="json")
            else:
                result[status_code] = dict(response)
        # 规范化：把 MediaType 嵌套结构（media_type_schema）转为标准 schema 字段。
        self._normalize_media_types(result)
        return result

    def _normalize_media_types(self, responses: dict[str, Any]) -> None:
        """将 MediaType 嵌套结构展开为标准的 schema/$ref 字段。

        openapi-pydantic 序列化后使用 media_type_schema 字段，需转换为 schema 字段。
        Reference 类型的 media_type_schema 序列化为 {\"ref\": \"#/...\"}，转换为 {\"$ref\": \"#/...\"}。

        :param responses: 响应字典，将被就地修改。
        """
        for response in responses.values():
            if not isinstance(response, dict):
                continue
            content = response.get("content")
            if not isinstance(content, dict):
                continue
            for media_type in content.values():
                self._normalize_media_type(media_type)

    def _normalize_media_type(self, media_type: dict[str, Any]) -> None:
        """将单个 MediaType 字典展开为标准 schema 字段。

        同时递归处理嵌套的 items、properties 中的 Reference。

        :param media_type: MediaType 字典，将被就地修改。
        """
        if not isinstance(media_type, dict):
            return
        media_type_schema = media_type.get("media_type_schema")
        if media_type_schema is None:
            return
        if isinstance(media_type_schema, dict):
            ref = media_type_schema.get("ref")
            if ref is not None:
                normalized = {"$ref": ref}
            else:
                normalized = media_type_schema
            # 递归处理嵌套的 Reference（如 array.items、object.properties）。
            self._normalize_references_in_schema(normalized)
            media_type["schema"] = normalized
        del media_type["media_type_schema"]

    def _normalize_references_in_schema(self, schema: dict[str, Any]) -> None:
        """递归将 schema 内嵌的 Reference 字段转换为 $ref 字段。

        处理 items（array）、properties.*（object）、additionalProperties 等嵌套位置。

        :param schema: schema 字典，将被就地修改。
        """
        if not isinstance(schema, dict):
            return
        # 处理 items（数组元素类型）。
        items = schema.get("items")
        if isinstance(items, dict) and "ref" in items and "$ref" not in items:
            ref_value = items.get("ref")
            schema["items"] = {"$ref": ref_value} if ref_value else items
        # 处理 properties（对象字段类型）。
        properties = schema.get("properties")
        if isinstance(properties, dict):
            for prop_name, prop_schema in properties.items():
                if isinstance(prop_schema, dict) and "ref" in prop_schema and "$ref" not in prop_schema:
                    ref_value = prop_schema.get("ref")
                    properties[prop_name] = {"$ref": ref_value} if ref_value else prop_schema

    def resolve_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        """解析 schema 引用，返回完整的 schema 定义。

        :param schema: 包含 $ref 的 schema 或完整 schema。
        :return: 解析后的完整 schema。
        """
        if "$ref" not in schema:
            return schema

        ref = schema["$ref"]
        if not ref.startswith("#/components/schemas/"):
            msg = f"Unsupported $ref format: {ref}"
            raise ValueError(msg)

        schema_name = ref.split("/")[-1]
        if not self._spec or not self._spec.components:
            schemas = {}
        else:
            schemas = self._spec.components.schemas or {}

        resolved = schemas.get(schema_name)
        if resolved is None:
            msg = f"Schema not found: {schema_name}"
            raise ValueError(msg)

        return resolved.model_dump(mode="json") if hasattr(resolved, "model_dump") else dict(resolved)
