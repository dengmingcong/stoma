"""OpenAPI 规范解析器。

从 OpenAPI Specification 文件中提取路径、方法、参数、schema 等信息，
供代码生成器使用。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml

# OpenAPI JSON Schema 文件路径（相对于当前模块）。
_OPENAPI_3_0_SCHEMA_PATH = Path(__file__).parent / "schemas" / "openapi-3.0.json"
_OPENAPI_3_1_SCHEMA_PATH = Path(__file__).parent / "schemas" / "openapi-3.1.json"


class OpenAPISchemaError(Exception):
    """OpenAPI schema 校验失败。"""

    pass


class OpenAPIParser:
    """OpenAPI 规范解析器。

    从 OpenAPI Specification 文件中提取路径、方法、参数、schema 等信息，
    供代码生成器使用。

    :var spec_path: OpenAPI 规范文件的路径。
    :vartype spec_path: Path
    """

    def __init__(self, spec_path: str | Path) -> None:
        """初始化解析器。

        :param spec_path: OpenAPI 规范文件路径（支持 YAML 或 JSON）。
        """
        self.spec_path = Path(spec_path)
        self._spec: dict[str, Any] | None = None

    def load(self) -> dict[str, Any]:
        """加载并解析 OpenAPI 规范文件。

        :return: 解析后的 OpenAPI 规范字典。
        :raise FileNotFoundError: 规范文件不存在。
        :raise ValueError: 规范文件格式错误。
        """
        if not self.spec_path.exists():
            msg = f"OpenAPI specification file not found: {self.spec_path}"
            raise FileNotFoundError(msg)

        content = self.spec_path.read_text(encoding="utf-8")

        try:
            if self.spec_path.suffix.lower() in {".yaml", ".yml"}:
                self._spec = yaml.safe_load(content)
            elif self.spec_path.suffix.lower() == ".json":
                self._spec = json.loads(content)
            else:
                # 尝试自动检测格式。
                try:
                    self._spec = yaml.safe_load(content)
                except yaml.YAMLError:
                    self._spec = json.loads(content)
        except (yaml.YAMLError, json.JSONDecodeError) as e:
            msg = f"Failed to parse OpenAPI specification: {e}"
            raise ValueError(msg) from e

        if not isinstance(self._spec, dict):
            msg = "OpenAPI specification must be a JSON object."
            raise ValueError(msg)

        return self._spec

    def validate(self) -> None:
        """使用 JSON Schema 校验 OpenAPI 规范。

        :raise OpenAPISchemaError: 规范不符合 JSON Schema。
        :raise ValueError: 尚未加载规范。
        """
        if self._spec is None:
            msg = "OpenAPI specification not loaded. Call load() first."
            raise ValueError(msg)

        # 根据 OpenAPI 版本选择对应的 JSON Schema。
        openapi_version = self.get_openapi_version()
        if openapi_version.startswith("3.1."):
            schema_path = _OPENAPI_3_1_SCHEMA_PATH
        elif openapi_version.startswith("3.0."):
            schema_path = _OPENAPI_3_0_SCHEMA_PATH
        else:
            msg = f"Unsupported OpenAPI version: {openapi_version}. Only 3.0.x and 3.1.x are supported."
            raise OpenAPISchemaError(msg)

        try:
            # 从本地文件加载 JSON Schema。
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            # 使用 schema 校验 OpenAPI 规范。
            jsonschema.validate(instance=self._spec, schema=schema)
        except jsonschema.ValidationError as e:
            msg = f"OpenAPI specification validation failed: {e.message}"
            raise OpenAPISchemaError(msg) from e
        except jsonschema.SchemaError as e:
            msg = f"Invalid JSON Schema: {e.message}"
            raise OpenAPISchemaError(msg) from e

    @property
    def spec(self) -> dict[str, Any]:
        """获取已加载的 OpenAPI 规范。

        :return: OpenAPI 规范字典。
        :raise RuntimeError: 尚未调用 load() 方法。
        """
        if self._spec is None:
            msg = "OpenAPI specification not loaded. Call load() first."
            raise RuntimeError(msg)
        return self._spec

    def get_openapi_version(self) -> str:
        """获取 OpenAPI 版本。

        :return: OpenAPI 版本号（如 "3.0.0"、"3.1.0"）。
        """
        return self.spec.get("openapi", "")

    def get_paths(self) -> dict[str, Any]:
        """获取所有路径。

        :return: paths 字典。
        """
        return self.spec.get("paths", {})

    def get_schemas(self) -> dict[str, Any]:
        """获取所有 schema 定义。

        :return: components/schemas 字典。
        """
        components = self.spec.get("components", {})
        return components.get("schemas", {})

    def get_security_schemes(self) -> dict[str, Any]:
        """获取所有安全 scheme 定义。

        :return: components/securitySchemes 字典。
        """
        components = self.spec.get("components", {})
        return components.get("securitySchemes", {})

    def get_info(self) -> dict[str, Any]:
        """获取 API 信息（title、description、version）。

        :return: info 字典。
        """
        return self.spec.get("info", {})
