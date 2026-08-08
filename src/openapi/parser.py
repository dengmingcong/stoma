"""通用且版本感知的 OpenAPI 规范解析器。

工厂按原始规范中的版本号注入 OpenAPI 3.0 或 3.1 的 Pydantic 模型类，
解析流程本身由同一个泛型类复用。类型参数统一使用 ``T`` 后缀并约束到
:class:`pydantic.BaseModel`；构造参数和实例属性则使用无后缀的 PascalCase
名称，以区分静态类型参数与运行时模型类。跨类型输入通过 ``object`` 和
``TypeGuard`` 收窄，避免把不同版本的模型合并成 Union。

参数层的 ``$ref`` 解析由工厂在上游通过 :func:`src.openapi.model_generator._expand_parameter_refs`
完成（基于 ``jsonref``），本模块只负责接收已展开的 spec 并做 Pydantic 校验
+ IR 构建，不再自行解析参数引用。
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, TypeGuard

import yaml
from pydantic import BaseModel, ValidationError

from src.openapi.model_generator import _detect_parameter_cycle, _expand_parameter_refs
from src.openapi.models import Endpoint
from src.openapi.models_types import SpecVersion
from src.openapi.reference_types import (
    OpenAPI30,
    OpenAPI31,
    Parameter30,
    Parameter31,
    Reference30,
    Reference31,
    RequestBody30,
    RequestBody31,
    Response30,
    Response31,
)


class OpenAPISchemaError(Exception):
    """OpenAPI schema 校验失败。"""

    pass


def _read_raw_spec(spec_path: Path) -> dict[str, Any]:
    """读取 YAML 或 JSON 格式的 OpenAPI 规范。

    :param spec_path: OpenAPI 规范文件路径。
    :return: 原始规范字典。
    :raise FileNotFoundError: 规范文件不存在。
    :raise ValueError: 文件后缀不受支持或顶层不是映射。
    """
    if not spec_path.exists():
        msg = f"OpenAPI specification file not found: {spec_path}"
        raise FileNotFoundError(msg)

    content = spec_path.read_text(encoding="utf-8")
    suffix = spec_path.suffix.lower()
    raw_spec: object
    if suffix in {".yaml", ".yml"}:
        raw_spec = yaml.safe_load(content)
    elif suffix == ".json":
        raw_spec = json.loads(content)
    else:
        msg = f"Unsupported file suffix: {suffix}. Supported: .yaml, .yml, .json"
        raise ValueError(msg)

    if not isinstance(raw_spec, dict):
        msg = "Invalid OpenAPI specification: expected a mapping at the top level"
        raise ValueError(msg)
    return {str(key): value for key, value in raw_spec.items()}


def _declared_version(raw_spec: dict[str, Any]) -> str:
    """返回规范声明的 OpenAPI 版本号。"""
    version = raw_spec.get("openapi", "")
    return version if isinstance(version, str) else ""


class OpenAPIParser[
    OpenAPIT: BaseModel,
    ReferenceT: BaseModel,
    ParameterT: BaseModel,
    RequestBodyT: BaseModel,
    ResponseT: BaseModel,
]:
    """按运行时注入模型类型解析 OpenAPI 3.0 或 3.1 规范。"""

    def __init__(
        self,
        *,
        OpenAPI: type[OpenAPIT],  # noqa: N803
        Reference: type[ReferenceT],  # noqa: N803
        Parameter: type[ParameterT],  # noqa: N803
        RequestBody: type[RequestBodyT],  # noqa: N803
        Response: type[ResponseT],  # noqa: N803
        spec_version: SpecVersion,
        raw_spec: dict[str, Any],
    ) -> None:
        """初始化解析器。

        :param OpenAPI: 当前版本的 OpenAPI 根模型类。
        :param Reference: 当前版本的引用模型类。
        :param Parameter: 当前版本的参数模型类。
        :param RequestBody: 当前版本的请求体模型类。
        :param Response: 当前版本的响应模型类。
        :param spec_version: 当前解析器处理的 OpenAPI 主版本。
        :param raw_spec: 已读取的原始规范字典（由工厂预填充）。
        """
        self.OpenAPI = OpenAPI
        self.Reference = Reference
        self.Parameter = Parameter
        self.RequestBody = RequestBody
        self.Response = Response
        self.spec_version = spec_version
        self._raw_spec_dict: dict[str, Any] = raw_spec
        self._spec: OpenAPIT | None = None
        self._has_payloads = False

    @property
    def raw_spec_dict(self) -> dict[str, Any]:
        """返回包含未展开 ``$ref`` 的原始规范字典。"""
        return self._raw_spec_dict

    @property
    def has_payloads(self) -> bool:
        """返回 paths 中是否包含 JSON 请求体或成功响应。"""
        return self._has_payloads

    def _is_reference(self, node: object) -> TypeGuard[ReferenceT]:
        """判断节点是否为当前版本的引用模型。"""
        return isinstance(node, self.Reference)

    def _is_parameter(self, node: object) -> TypeGuard[ParameterT]:
        """判断节点是否为当前版本的参数模型。"""
        return isinstance(node, self.Parameter)

    def _is_request_body(self, node: object) -> TypeGuard[RequestBodyT]:
        """判断节点是否为当前版本的请求体模型。"""
        return isinstance(node, self.RequestBody)

    def _is_response(self, node: object) -> TypeGuard[ResponseT]:
        """判断节点是否为当前版本的响应模型。"""
        return isinstance(node, self.Response)

    def load(self) -> None:
        """通过 ``self.OpenAPI`` 校验原始规范字典。"""
        try:
            self._spec = self.OpenAPI.model_validate(self._raw_spec_dict)
        except ValidationError as error:
            msg = f"Failed to parse OpenAPI specification: {error}"
            raise ValueError(msg) from error

    def _resolve_one(self, node: object) -> ParameterT:
        """校验节点是 Parameter（jsonref 上游已展开 ref）。"""
        if self._is_parameter(node):
            return node
        msg = f"Expected Parameter, got {type(node).__name__}"
        raise OpenAPISchemaError(msg)

    def _merge_path_item_params(
        self,
        path_item_params: Sequence[object],
        operation_params: Sequence[object],
    ) -> list[ParameterT]:
        """合并路径项参数和操作参数，操作级同名参数优先。"""
        path_resolved = [self._resolve_one(parameter) for parameter in path_item_params]
        operation_resolved = [self._resolve_one(parameter) for parameter in operation_params]
        operation_keys = {self._parameter_key(parameter) for parameter in operation_resolved}
        merged = [parameter for parameter in path_resolved if self._parameter_key(parameter) not in operation_keys]
        merged.extend(operation_resolved)
        return merged

    @staticmethod
    def _parameter_key(parameter: BaseModel) -> tuple[str, str]:
        """返回参数覆盖规则使用的 ``(name, in)`` 键。"""
        data = parameter.model_dump(mode="json", by_alias=True)
        name = data.get("name", "")
        location = data.get("in", "")
        return str(name), str(location)

    @staticmethod
    def _operations(path_item: object) -> dict[str, object]:
        """返回路径项中受支持的 HTTP 操作。"""
        operations: dict[str, object] = {}
        for method in ("get", "post", "put", "patch", "delete"):
            operation = getattr(path_item, method, None)
            if operation is not None:
                operations[method] = operation
        return operations

    @staticmethod
    def _as_sequence(value: object) -> Sequence[object]:
        """把第三方模型中的可选参数序列规范化为空序列或对象序列。"""
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            return value
        return ()

    @staticmethod
    def _has_json_schema(node: BaseModel) -> bool:
        """判断请求体或响应是否声明 application/json schema。"""
        content = getattr(node, "content", None)
        if not isinstance(content, dict):
            return False
        media_type = content.get("application/json")
        return media_type is not None and getattr(media_type, "media_type_schema", None) is not None

    def _response_map(self, value: object) -> dict[str, ResponseT] | None:
        """收窄操作响应映射中的当前版本响应模型。"""
        if not isinstance(value, dict):
            return None
        return {str(status): response for status, response in value.items() if self._is_response(response)}

    def validate_operation_ids(self) -> None:
        """校验所有操作均有非空 ``operationId``。"""
        if self._spec is None:
            msg = "OpenAPI specification not loaded. Call load() first."
            raise RuntimeError(msg)

        paths = getattr(self._spec, "paths", None)
        if not isinstance(paths, dict):
            return
        for path, path_item in paths.items():
            for method, operation in self._operations(path_item).items():
                operation_id = getattr(operation, "operationId", None)
                if not isinstance(operation_id, str) or not operation_id.strip():
                    msg = f"operationId is required for {method.upper()} {path}"
                    raise OpenAPISchemaError(msg)

    def get_endpoints(self) -> list[Endpoint[ParameterT, RequestBodyT, ResponseT]]:
        """返回当前规范中的结构化 endpoint 列表。"""
        if self._spec is None or self._raw_spec_dict is None:
            msg = "OpenAPI specification not loaded. Call load() first."
            raise RuntimeError(msg)

        endpoints: list[Endpoint[ParameterT, RequestBodyT, ResponseT]] = []
        paths = getattr(self._spec, "paths", None)
        if not isinstance(paths, dict):
            self._has_payloads = False
            return endpoints

        has_payloads = False
        for path, path_item in paths.items():
            path_params = self._as_sequence(getattr(path_item, "parameters", None))
            for method, operation in self._operations(path_item).items():
                request_body_node = getattr(operation, "requestBody", None)
                request_body = request_body_node if self._is_request_body(request_body_node) else None
                if request_body is not None and self._has_json_schema(request_body):
                    has_payloads = True

                response_nodes = getattr(operation, "responses", None)
                responses = self._response_map(response_nodes)
                if responses and any(
                    self._has_json_schema(response)
                    for status, response in responses.items()
                    if status in {"200", "201"}
                ):
                    has_payloads = True

                operation_id = getattr(operation, "operationId", None)
                summary = getattr(operation, "summary", None)
                description = getattr(operation, "description", None)
                operation_params = self._as_sequence(getattr(operation, "parameters", None))
                endpoint = Endpoint[ParameterT, RequestBodyT, ResponseT](
                    operation_id=operation_id if isinstance(operation_id, str) else "",
                    method=method,
                    path=str(path),
                    summary=summary if isinstance(summary, str) else None,
                    description=description if isinstance(description, str) else None,
                    parameters=self._merge_path_item_params(path_params, operation_params),
                    request_body=request_body,
                    responses=responses,
                    spec_version=self.spec_version,
                )
                endpoints.append(endpoint)

        self._has_payloads = has_payloads
        return endpoints


def make_openapi_parser(spec_path: str | Path) -> OpenAPIParser[Any, Any, Any, Any, Any]:
    """按规范声明的版本构造参数化解析器。

    工厂会先沿 :func:`src.openapi.model_generator._detect_parameter_cycle`
    检查 ``components.parameters`` 中的 ``$ref`` 链是否有环，遇到环立即
    抛出 :class:`OpenAPISchemaError`（避免 jsonref 陷入无限递归）。
    随后调用 :func:`src.openapi.model_generator._expand_parameter_refs`
    在 ``paths[*]`` 操作级 ``parameters`` 上就地展开 ``$ref``，
    ``requestBody`` 与 ``responses`` 中的引用保持原样。

    :param spec_path: OpenAPI 规范文件路径。
    :return: 注入对应版本模型类的解析器。
    :raise OpenAPISchemaError: 参数 ``$ref`` 链存在环，或 jsonref 解析失败。
    :raise ValueError: 规范声明的版本不受支持。
    """
    path = Path(spec_path)
    raw_spec = _read_raw_spec(path)
    cycle_path = _detect_parameter_cycle(raw_spec)
    if cycle_path is not None:
        msg = f"Cycle detected in parameter $ref chain: {cycle_path}"
        raise OpenAPISchemaError(msg)
    raw_spec = _expand_parameter_refs(raw_spec)
    version = _declared_version(raw_spec)
    if version.startswith("3.0."):
        return OpenAPIParser[OpenAPI30, Reference30, Parameter30, RequestBody30, Response30](
            OpenAPI=OpenAPI30,
            Reference=Reference30,
            Parameter=Parameter30,
            RequestBody=RequestBody30,
            Response=Response30,
            spec_version="3.0",
            raw_spec=raw_spec,
        )
    if version.startswith("3.1."):
        return OpenAPIParser[OpenAPI31, Reference31, Parameter31, RequestBody31, Response31](
            OpenAPI=OpenAPI31,
            Reference=Reference31,
            Parameter=Parameter31,
            RequestBody=RequestBody31,
            Response=Response31,
            spec_version="3.1",
            raw_spec=raw_spec,
        )
    msg = f"Unsupported OpenAPI version: {version}. Only 3.0.x and 3.1.x are supported."
    raise ValueError(msg)
