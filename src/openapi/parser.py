"""OpenAPI 规范解析器。

使用 openapi-pydantic 解析 OpenAPI Specification 文件，
提取路径、方法、参数、schema 等信息，供代码生成器使用。
"""

import json
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


def _fill_schema_titles(spec: dict[str, Any]) -> None:
    """给 components.schemas 补全 title，并递归处理嵌套的 schema。

    在 prance 展开之前调用，用 schema 的 key 作为 title。
    同时递归处理 properties、items、allOf、oneOf、anyOf 中的嵌套 schema。
    这样展开后的 schema 会保留 title，renderer 不需要再查 components。

    :param spec: OpenAPI 规范字典。
    """
    schemas = spec.get("components", {}).get("schemas", {})
    if not isinstance(schemas, dict):
        return

    def fill_title(schema: dict[str, Any]) -> None:
        if not isinstance(schema, dict):
            return
        # 递归处理 allOf/oneOf/anyOf
        for key in ("allOf", "oneOf", "anyOf"):
            items = schema.get(key)
            if isinstance(items, list):
                for item in items:
                    fill_title(item)
        # 递归处理 items（array 的 items）
        items = schema.get("items")
        if isinstance(items, dict):
            fill_title(items)
        # 递归处理 properties
        properties = schema.get("properties")
        if isinstance(properties, dict):
            for prop in properties.values():
                fill_title(prop)

    for name, schema in schemas.items():
        if isinstance(schema, dict) and not schema.get("title"):
            schema["title"] = name
        if isinstance(schema, dict):
            fill_title(schema)


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
            raw_dict = yaml.safe_load(content)
        elif suffix == ".json":
            raw_dict = json.loads(content)
        else:
            msg = f"Unsupported file suffix: {suffix}. Supported: .yaml, .yml, .json"
            raise ValueError(msg)

        # 先检查版本，不支持则提前报错。
        openapi_version = raw_dict.get("openapi", "") if isinstance(raw_dict, dict) else ""
        if not openapi_version.startswith(("3.0.", "3.1.")):
            msg = f"Unsupported OpenAPI version: {openapi_version}. Only 3.0.x and 3.1.x are supported."
            raise ValueError(msg)

        # 给 components.schemas 补全 title，让 prance 展开后的内联副本
        # 也带 title；这是 datamodel-codegen 跨 components 和 paths 做
        # 去重时的关键标识（仅靠 dict key 不够，必须 title 也一致）。
        _fill_schema_titles(raw_dict)

        try:
            modified_content = yaml.dump(raw_dict) if suffix in {".yaml", ".yml"} else json.dumps(raw_dict)
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
