"""OpenAPI 规范解析器。

使用 openapi-pydantic 解析 OpenAPI Specification 文件，
提取路径、方法、参数、schema 等信息，供代码生成器使用。
"""

import json
import re
from pathlib import Path
from typing import Any

import yaml
from openapi_pydantic import OpenAPI, Reference
from openapi_pydantic.v3.v3_1 import Operation as Operation31

from src.openapi.models import Endpoint

Operation = Operation31


def _operation_id_to_pascal(operation_id: str) -> str:
    """把 operationId 转为 PascalCase 类名。

    支持 snake_case、camelCase、PascalCase 和含连字符四种格式。

    :param operation_id: 原始 operationId。
    :return: PascalCase 类名。
    """
    normalized = operation_id.replace("-", "_")
    words = re.split(r"[_-]+|(?<=[a-z0-9])(?=[A-Z])", normalized)
    return "".join(word.capitalize() for word in words if word)


def _ref_to_model_name(ref: str) -> str:
    """从 ``$ref`` 字符串提取 model 名（末段）。

    :param ref: 形如 ``"#/components/schemas/User"`` 的 $ref 字符串。
    :return: 末段作为 model 名（``"User"``）。
    """
    return ref.rsplit("/", 1)[-1]


def _is_inline_object(schema: dict[str, Any]) -> bool:
    """判断 schema 是否是需要注入 title 的「内联 object」。

    意义：``_fill_schema_titles`` 给路径里 path.requestBody / responses
    的 schema 注入 ``title = {OperationId}Request``，让
    datamodel-codegen 跨 components / paths 做去重。但**不是所有 schema
    都该被注入**——本函数集中 4 条"不要注入"的条件，把"该不该注入"这个
    概念命名下来，让 callsite 写成 ``if _is_inline_object(x)`` 即可。

    4 条条件（**全部不满足**才返回 ``True**）：

    1. 不含 ``$ref``——datamodel-codegen 自己会从 ref 末段取名（如
       ``$ref: '#/components/schemas/User'`` 自动生成 ``class User``），
       注入 title 会导致重复类。
    2. 没有现成 title——已有 title 说明 prance 复制时已带 title
       （来自 components.schemas 命名），覆盖会破坏跨
       components / paths 的去重。
    3. ``type: object``——标量（string/number/...）和 array 不需要单独
       模型类，注入 title 没用。
    4. ``properties`` 非空——空 object 注入 title 后 datamodel-codegen
       也建不出有意义的 Pydantic 类。

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
        self._raw_spec_dict: dict[str, Any] | None = None
        self._spec: OpenAPI | None = None
        self._has_payloads: bool = False

    @property
    def raw_spec_dict(self) -> dict[str, Any]:
        """raw spec 字典（含未展开的 ``$ref``），给 ``generate_models`` 使用。"""
        if self._raw_spec_dict is None:
            raise RuntimeError("call load() first")
        return self._raw_spec_dict

    @property
    def spec_dict(self) -> dict[str, Any]:
        """同 :attr:`raw_spec_dict`（保留兼容旧接口）。"""
        return self.raw_spec_dict

    @property
    def has_payloads(self) -> bool:
        """``load()`` 后：paths 中是否找到任何 request body 或 200/201 响应的 ``application/json``。

        由 :meth:`get_endpoints` 在遍历 paths 时设置，避免 cli 重复 walk。
        """
        return self._has_payloads

    def load(self) -> None:
        """加载 OpenAPI 规范文件。

        读 YAML/JSON → 用 openapi-pydantic 构造 Pydantic 模型。
        不展开 ``$ref``——renderer 自己读 ``Reference.ref`` 字符串。

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

        # 直接用 raw spec 构造 Pydantic 模型——$ref 字段变成 Reference 实例。
        # 不再 prance 展开，不再 _fill_schema_titles 注入 title。
        self._raw_spec_dict = raw_spec_dict
        try:
            self._spec = OpenAPI.model_validate(raw_spec_dict)
        except Exception as e:
            raise ValueError(f"Failed to parse OpenAPI specification: {e}") from e

    def get_openapi_version(self) -> str:
        """获取 OpenAPI 版本。

        :return: OpenAPI 版本号（如 "3.0.0"、"3.1.0"）。
        """
        if self._raw_spec_dict is None:
            return ""
        return self._raw_spec_dict.get("openapi", "")

    def validate_operation_ids(self) -> None:
        """校验所有 operation 都有非空 operationId。

        ``datamodel-code-generator`` 的 ``use_operation_id_as_name=True`` 严格模式
        要求每个 operation 必须有 operationId，缺失时 dmcg 会报错，但报错信息
        对 stoma 用户不友好。本方法在调用 dmcg 之前提前校验，抛清晰错误。

        本方法为独立方法，不放在 :meth:`get_endpoints` 里——因为 ``get_endpoints()``
        在 cli.py 里**不在 try/except 块内**（只有 ``parser.load()`` 在），
        从 ``get_endpoints()`` 抛的异常会泄露 stack trace。独立方法让 cli.py
        在已有 try 块里显式调用 ``parser.validate_operation_ids()``，错误走
        ``typer.BadParameter`` 友好路径。

        :raise RuntimeError: 尚未调用 ``load()`` 方法。
        :raise OpenAPISchemaError: 存在缺失 operationId 的 operation。
        """
        if self._spec is None:
            msg = "OpenAPI specification not loaded. Call load() first."
            raise RuntimeError(msg)

        if not self._spec.paths:
            return

        for path, path_item in self._spec.paths.items():
            method_to_operation = {
                method: operation
                for method in ("get", "post", "put", "patch", "delete")
                if (operation := getattr(path_item, method))
            }
            operation: Operation
            for method, operation in method_to_operation.items():
                if not (operation.operationId and operation.operationId.strip()):
                    msg = f"operationId is required for {method.upper()} {path}"
                    raise OpenAPISchemaError(msg)

    def _schema_to_model_name(
        self,
        schema: Any,
        kind: str,
        operation_id: str,
    ) -> str | None:
        """从 schema 字段提取 model 名。

        :param schema: openapi-pydantic 的 Schema | Reference | None。
        :param kind: ``"request"`` 或 ``"response"``——决定 fallback 命名。
        :param operation_id: 当前 operation 的 operationId（用于 fallback）。
        :return: model 名；没有 body / response 时返回 None。
        """
        if schema is None:
            return None
        if isinstance(schema, Reference):
            return _ref_to_model_name(schema.ref)
        # inline object（Pydantic Schema 实例，没有 title 因为我们不再注入）
        suffix = "Request" if kind == "request" else "Response"
        return f"{operation_id}{suffix}"

    def get_endpoints(self) -> list[Endpoint]:
        """获取所有 endpoint 的结构化信息。

        遍历 raw spec 的 paths，对每个 operation 计算 ``request_body_type``
        和 ``response_type``（从 ``Reference.ref`` 末段或 operationId 派生）。
        同时设置 ``_has_payloads`` 供 cli 判断是否要生成 ``models.py``。

        :return: endpoint 列表。
        :raise RuntimeError: 尚未调用 ``load()`` 方法。
        """
        if self._spec is None or self._raw_spec_dict is None:
            msg = "OpenAPI specification not loaded. Call load() first."
            raise RuntimeError(msg)

        endpoints: list[Endpoint] = []
        has_payload = False
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
                operation_id = operation.operationId or ""

                # 请求体 model 名
                request_body_type: str | None = None
                rb = operation.requestBody
                if rb is not None:
                    content = rb.content or {}
                    json_content = content.get("application/json")
                    if json_content is not None:
                        schema = getattr(json_content, "media_type_schema", None)
                        request_body_type = self._schema_to_model_name(
                            schema, "request", operation_id
                        )
                        if request_body_type is not None:
                            has_payload = True

                # 响应 model 名（200/201 优先）
                response_type: str | None = None
                if operation.responses:
                    for status in ("200", "201"):
                        resp = operation.responses.get(status)
                        if resp is None:
                            continue
                        content = resp.content or {}
                        json_content = content.get("application/json")
                        if json_content is None:
                            continue
                        schema = getattr(json_content, "media_type_schema", None)
                        response_type = self._schema_to_model_name(
                            schema, "response", operation_id
                        )
                        if response_type is not None:
                            has_payload = True
                        break

                endpoint = Endpoint(
                    operation_id=operation_id,
                    method=method,
                    path=path,
                    summary=operation.summary,
                    description=operation.description,
                    parameters=operation.parameters or [],
                    request_body=operation.requestBody,
                    responses=operation.responses,
                )
                endpoints.append(endpoint)

        self._has_payloads = has_payload
        return endpoints
