"""OpenAPI 规范解析器。

使用 openapi-pydantic 解析 OpenAPI Specification 文件，
提取路径、方法、参数、schema 等信息，供代码生成器使用。
"""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml
from openapi_pydantic import OpenAPI, Reference
from pydantic import TypeAdapter
from referencing import Registry, Resource
from referencing.exceptions import Unresolvable

from src.openapi.models import Endpoint, Operation, RequestBody, Response
from src.openapi.models import Parameter as ParameterUnion

_PARAMETER_UNION_ADAPTER: TypeAdapter[ParameterUnion] = TypeAdapter(ParameterUnion)


class OpenAPISchemaError(Exception):
    """OpenAPI schema 校验失败。"""

    pass


def _build_registry(raw_spec: dict[str, Any]) -> Registry[dict[str, Any]]:
    """把 raw spec 包装为用于解析 JSON Pointer 的注册表。

    :param raw_spec: 完整的 OpenAPI spec 字典，包含未展开的 ``$ref``。
    :return: 可解析 ``#/components/parameters/<name>`` 等内部引用的注册表。
    """
    resource = Resource.opaque(raw_spec)
    registry: Registry[dict[str, Any]] = Registry()
    registry = registry.with_resource(uri="", resource=resource)
    return registry


def _resolve_parameter_refs(
    raw_spec: dict[str, Any],
    params: Sequence[ParameterUnion | Reference],
) -> list[ParameterUnion]:
    """展开参数列表中的引用元素。

    支持链式 ``$ref``，并拒绝循环引用、外部引用和不存在的目标。

    :param raw_spec: 完整的 OpenAPI spec 字典。
    :param params: 元素为参数或引用的参数列表。
    :return: 所有引用均已展开的参数列表。
    :raise OpenAPISchemaError: 引用成环、指向外部资源或无法解析时。
    """
    registry = _build_registry(raw_spec)
    return [_resolve_one(param, registry, frozenset()) for param in params]


def _resolve_one(
    node: ParameterUnion | Reference,
    registry: Registry[dict[str, Any]],
    seen: frozenset[str],
) -> ParameterUnion:
    """解析单个参数或引用。

    遇到引用时递归展开，并检测链式引用中的环。外部引用和无法解析的
    JSON Pointer 会转换为 ``OpenAPISchemaError``。

    :param node: 待解析的参数或引用。
    :param registry: 包含完整 OpenAPI spec 的引用注册表。
    :param seen: 当前解析链中已经访问的引用集合。
    :return: 展开引用后的参数。
    :raise OpenAPISchemaError: 引用成环、指向外部资源或无法解析时。
    """
    if not isinstance(node, Reference):
        return node

    if node.ref in seen:
        path = " -> ".join((*seen, node.ref))
        raise OpenAPISchemaError(f"Cycle detected resolving parameter $ref: {path}")

    if not node.ref.startswith("#/components/parameters/"):
        raise OpenAPISchemaError(
            f"Unsupported parameter $ref: {node.ref!r}. "
            "Only '#/components/parameters/<name>' is supported."
        )

    try:
        resolved = registry.resolver().lookup(node.ref)
    except Unresolvable as error:
        raise OpenAPISchemaError(
            f"Cannot resolve parameter $ref: {node.ref!r}. "
            "Component not found in '#/components/parameters/'."
        ) from error

    contents = resolved.contents
    if "$ref" in contents:
        return _resolve_one(
            Reference.model_validate({"$ref": contents["$ref"]}),
            registry,
            seen | {node.ref},
        )

    parameter_contents = {key: value for key, value in contents.items() if key != "$ref"}
    return _PARAMETER_UNION_ADAPTER.validate_python(parameter_contents)


def _merge_path_item_params(
    path_item_params: Sequence[ParameterUnion | Reference],
    operation_params: Sequence[ParameterUnion | Reference],
    raw_spec: dict[str, Any],
) -> list[ParameterUnion]:
    """合并路径项级和操作级参数。

    操作级中 ``(name, in)`` 相同的参数覆盖路径项级参数。结果先保留路径项级
    独占参数，再追加操作级独占参数和覆盖参数，并确保所有引用均已展开。

    :param path_item_params: 路径项级参数列表。
    :param operation_params: 操作级参数列表。
    :param raw_spec: 完整的 OpenAPI spec 字典。
    :return: 按覆盖规则合并且已展开引用的参数列表。
    :raise OpenAPISchemaError: 任一参数引用成环、指向外部资源或无法解析时。
    """
    path_item_resolved = _resolve_parameter_refs(raw_spec, path_item_params)
    operation_resolved = _resolve_parameter_refs(raw_spec, operation_params)
    operation_keys = {
        (parameter.name, parameter.param_in.value if parameter.param_in else "")
        for parameter in operation_resolved
    }

    merged = [
        parameter
        for parameter in path_item_resolved
        if (parameter.name, parameter.param_in.value if parameter.param_in else "") not in operation_keys
    ]
    merged.extend(operation_resolved)
    return merged


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

    def get_endpoints(self) -> list[Endpoint]:
        """获取所有 endpoint 的结构化信息。

        遍历 raw spec 的 paths，检查每个 operation 是否带 JSON schema（request body
        或 200/201 响应）。同时设置 ``_has_payloads`` 供 cli 判断是否要生成
        ``models.py``。逐 operation 合并 path_item 级与 operation 级的 parameters，
        并展开其中的 ``$ref`` 元素。

        :return: endpoint 列表。
        :raise RuntimeError: 尚未调用 ``load()`` 方法。
        :raise OpenAPISchemaError: 参数 ``$ref`` 解析失败（环、外部 ref、组件不存在）。
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

                # 请求体是否带 JSON schema
                rb = operation.requestBody
                # 只内联 RequestBody；$ref 的 requestBody 是 Reference，没法取 content。
                if isinstance(rb, RequestBody):
                    content = rb.content or {}
                    json_content = content.get("application/json")
                    if json_content is not None and getattr(json_content, "media_type_schema", None) is not None:
                        has_payload = True

                # 响应是否带 JSON schema（200/201 优先）
                if operation.responses:
                    for status in ("200", "201"):
                        resp = operation.responses.get(status)
                        # 只内联 Response；None = 不存在，Reference = $ref 没法取 content。
                        if not isinstance(resp, Response):
                            continue
                        content = resp.content or {}
                        json_content = content.get("application/json")
                        if json_content is None:
                            continue
                        if getattr(json_content, "media_type_schema", None) is not None:
                            has_payload = True
                        break

                endpoint = Endpoint(
                    operation_id=operation_id,
                    method=method,
                    path=path,
                    summary=operation.summary,
                    description=operation.description,
                    parameters=_merge_path_item_params(
                        path_item.parameters or [],
                        operation.parameters or [],
                        self._raw_spec_dict,
                    ),
                    request_body=operation.requestBody,
                    responses=operation.responses,
                )
                endpoints.append(endpoint)

        self._has_payloads = has_payload
        return endpoints
