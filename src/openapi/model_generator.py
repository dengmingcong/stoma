"""``datamodel-code-generator`` 的 Python API 封装。

stoma 的 ``make`` 命令在预处理 spec 后调用本模块生成 ``models.py``，
通过固化 :func:`generate` 的参数确保所有 spec 走相同的输出约定
（Pydantic v2、snake_case 字段、``$ref`` 解析、操作 ID 命名）。

参考：
- https://github.com/koxudaxi/datamodel-code-generator
- https://datamodel-code-generator.koxudaxi.dev/
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import jsonref
from datamodel_code_generator import (
    InputFileType,
    OpenAPIScope,
    PythonVersion,
    generate,
)
from datamodel_code_generator.enums import DataModelType

from src.exceptions import OpenAPISchemaError

# 循环检测只沿 ``#/components/parameters/`` 开头的内部 ``$ref`` 展开；
# 指向 schema 或外部文件的 ``$ref`` 不属于参数链，遇到即停止。
_PARAMETER_REF_PREFIX: str = "#/components/parameters/"


def generate_models(spec_dict: dict[str, Any], output_path: Path) -> None:
    """调用 ``datamodel-code-generator`` 生成 Pydantic v2 模型到 ``output_path``。

    输入：解析后的 OpenAPI 规范字典。
    输出：单个 ``models.py``，包含 spec 中所有 ``$ref`` schemas + inline
    objects（带由 operationId 派生的 PascalCase 类名，如 ``createItem`` → ``CreateItemRequest``）。

    约束字段和 alias 字段均以 Pydantic v2 风格的 ``Annotated[T, Field(...)]`` 形式输出
    （启用 dmcg 的 ``field_constraints=True`` + ``use_annotated=True``）。这取代了默认的 v1 风格
    ``conint(...)``/``constr(...)`` —— 后者会被 Pylance 静态分析为非法类型形式
    并触发 ``reportInvalidTypeForm`` 误报；也替代了 ``T = Field(...)`` 这种
    把类型与默认值揉在同一位置的写法，输出更符合 PEP 593 的习惯，并对
    Pylance / mypy 等静态检查器更友好。

    :param spec_dict: 解析后的 OpenAPI 规范字典。
    :param output_path: ``models.py`` 的输出路径。父目录如不存在会自动创建。
    :raise RuntimeError: ``datamodel-code-generator`` 调用失败且未产出文件。
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        generate(
            input_=spec_dict,
            output=output_path,
            input_file_type=InputFileType.OpenAPI,
            output_model_type=DataModelType.PydanticV2BaseModel,
            target_python_version=PythonVersion.PY_312,
            field_constraints=True,
            use_annotated=True,
            snake_case_field=True,
            use_double_quotes=True,
            use_union_operator=True,
            use_operation_id_as_name=True,
            openapi_scopes=[OpenAPIScope.Schemas, OpenAPIScope.Paths],
        )
    except Exception as e:
        msg = f"datamodel-code-generator 调用失败: {e}"
        raise RuntimeError(msg) from e

    if not output_path.exists():
        msg = f"datamodel-code-generator 未生成文件: {output_path}"
        raise RuntimeError(msg)


def _detect_parameter_cycle(raw_spec: dict[str, Any]) -> str | None:
    """深度优先遍历 ``components.parameters``，检测 ``$ref`` 链中的环。

    仅沿 ``#/components/parameters/<name>`` 这一前缀向下展开：
    指向 schema 或外部文件的 ``$ref`` 不属于参数链，遇到即停止，
    因此不会误把 ``components.schemas`` 之间的相互引用当作参数环。

    :param raw_spec: 原始 OpenAPI 规范字典。
    :return: 发现环时返回形如 ``"A -> B -> A"`` 的路径字符串；
        否则返回 ``None``。路径以展开起点参数名闭合。
    """
    components_obj = raw_spec.get("components")
    if not isinstance(components_obj, dict):
        return None
    params_obj = components_obj.get("parameters")
    if not isinstance(params_obj, dict):
        return None

    def walk(name: str, seen: frozenset[str], path: tuple[str, ...]) -> str | None:
        if name in seen:
            return " -> ".join((*path, name))
        value: object = params_obj.get(name)
        if not isinstance(value, dict):
            return None
        ref: object = value.get("$ref")
        if not isinstance(ref, str):
            return None
        if not ref.startswith(_PARAMETER_REF_PREFIX):
            return None
        target = ref[len(_PARAMETER_REF_PREFIX) :]
        return walk(target, seen | {name}, (*path, name))

    for name in params_obj:
        if not isinstance(name, str):
            continue
        result = walk(name, frozenset(), ())
        if result is not None:
            return result
    return None


def _expand_path_refs(
    raw_spec: dict[str, Any],
) -> tuple[dict[str, Any], dict[tuple[str, str], dict[str, Any]]]:
    """在 ``raw_spec`` 内展开 ``paths[*]`` 下 ``parameters`` 与 ``requestBody`` 中的 ``$ref``。

    OpenAPI 允许 ``parameters`` 出现在两个层级：
    path item 级（直接挂在 ``paths[/x]`` 上，对该路径下所有 operation 生效）
    和 operation 级（挂在 ``paths[/x][<method>]`` 上）。两者都会被纳入合成规范
    并展开，而 ``responses``、``summary``、``description``、``security`` 等键被丢弃，
    原样附带 ``components``，交给 :func:`jsonref.replace_refs` 立即解析。

    ``parameters`` 的展开结果以 path item 和 method 两个维度回写到 ``raw_spec``：
    path item 级 ``parameters`` 直接落到 ``raw_spec["paths"][<path>]["parameters"]``，
    operation 级 ``parameters`` 落到对应方法上；其余字段保持不变。

    ``requestBody`` 的展开结果**不写回** ``raw_spec``，而是抽离到返回的
    ``request_body_map`` 字典中（key 是 ``(path, method_upper)`` 元组，value
    是展开后的 ``requestBody`` 字典），由 renderer 通过 ``endpoint.expanded_raw_request_body``
    读取。这样既避免污染原始 ``$.ref`` 字符串（datamodel-code-generator
    会自行处理原样 ``$ref``），又让 renderer 无需重复 jsonref 调用。

    ``jsonref.JsonRefError``（例如指向外部文件且无法解析的 ``$ref``）
    会被包装为 :class:`OpenAPISchemaError` 抛出。

    :param raw_spec: 待修改的 OpenAPI 规范字典（会被就地修改）。
    :return: ``(modified_raw_spec, request_body_map)`` 二元组。
        ``modified_raw_spec`` 是写回 ``parameters`` 展开结果后的 ``raw_spec``；
        ``request_body_map`` 的 key 是 ``(path, method_upper)``，value 是
        展开后的 ``requestBody`` 字典。
    :raise OpenAPISchemaError: ``jsonref`` 解析参数或 requestBody ``$ref`` 失败。
    """
    original_paths = raw_spec.get("paths")
    if not isinstance(original_paths, dict):
        # 没有 paths 字段时按空 spec 处理：建一个空 dict 占位，方便后续循环不报错。
        original_paths = {}
        raw_spec["paths"] = original_paths

    # ---- 第 1 步：构造合成规范 ----
    # 合成规范只包含 ``parameters`` + ``requestBody`` 键（path item 级 + 各 operation 级），
    # 其余键（``responses``、``summary``、``description`` 等）原样不在合成 spec 中出现，
    # 因此 jsonref 不会展开它们的 ``$ref``——datamodel-code-generator 仍按
    # ``components.schemas`` 里的命名规则生成对应的 Pydantic 类。
    synthetic_paths: dict[str, Any] = {}
    request_body_synthetic: dict[tuple[str, str], dict[str, Any]] = {}
    for path_key, path_item in original_paths.items():
        if not isinstance(path_item, dict):
            # path item 不是 dict（如 yaml 里写成了字符串）的容错：跳过。
            continue
        filtered_item: dict[str, Any] = {}
        # OpenAPI 允许 ``parameters`` 挂在 path item 上（对该路径下所有
        # operation 生效），这里一并收入合成 spec。
        if "parameters" in path_item:
            filtered_item["parameters"] = path_item["parameters"]
        # 各 operation（``GET``/``POST``/``PUT``/``PATCH``/``DELETE``/``HEAD``/``OPTIONS``/``TRACE``）
        # 也可能有自己的 ``parameters`` 与 ``requestBody``，同样收入合成 spec。
        for method_key, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            method_synthetic: dict[str, Any] = {}
            if "parameters" in operation:
                method_synthetic["parameters"] = operation["parameters"]
            if "requestBody" in operation:
                method_synthetic["requestBody"] = operation["requestBody"]
                # 记录 (path, method_upper) 以便回抽展开后的 requestBody。
                request_body_synthetic[(str(path_key), str(method_key).upper())] = operation["requestBody"]
            if method_synthetic:
                filtered_item[str(method_key)] = method_synthetic
        # 只有当这个路径至少有一处 ``parameters`` 或 ``requestBody`` 时才纳入合成 spec。
        # 没有任何引用内容的路径加进去只会让 jsonref 多走无意义的分支。
        if filtered_item:
            synthetic_paths[str(path_key)] = filtered_item

    synthetic: dict[str, Any] = {
        "paths": synthetic_paths,
        # ``components`` 必须原样附带：jsonref 通过它解析 ``$ref`` 指向的目标。
        # body / response 的 ``$ref`` 指向的 schema 也在 ``components.schemas`` 里。
        "components": raw_spec.get("components", {}),
    }

    # ---- 第 2 步：调用 jsonref 一次性展开 ----
    # ``proxies=False``：直接返回 dict，而不是 JsonRef 代理对象（代理对象
    # 会让下游 Pydantic 校验失败，因为 Pydantic 不认识代理类型）。
    # ``lazy_load=False``：立即求值所有 ``$ref``，避免后续访问时的延迟副作用。
    try:
        expanded = jsonref.replace_refs(synthetic, proxies=False, lazy_load=False)
    except jsonref.JsonRefError as exc:
        # 外部 ref（如 ``common.yaml#/...``）或解析失败——包装为业务异常，
        # 保留原始异常链便于调试（``from exc``）。
        msg = f"Failed to resolve parameter or requestBody $ref: {exc}"
        raise OpenAPISchemaError(msg) from exc

    # ---- 第 3 步：回写展开结果到原 raw_spec ----
    # 仅替换 ``parameters`` 键；``requestBody`` 不写回，由 request_body_map 单独承载。
    # 其他键（如 ``summary``、``requestBody`` 本身）保持原样不动。
    expanded_paths: object = expanded["paths"] if isinstance(expanded, dict) else {}
    if not isinstance(expanded_paths, dict):
        # 防御性 fallback：jsonref 正常情况下总返回 dict，但若上游出错时
        # 调用方已经在 except 中处理过了，这里只是兜底。
        expanded_paths = {}

    for path_key, path_item in expanded_paths.items():
        if not isinstance(path_item, dict):
            continue
        # 取原 path item 作为写入目标——原 spec 可能还有 ``summary``、
        # ``description`` 之类的字段需要保留，不能直接覆盖整个 path item。
        target_path_item = original_paths.get(path_key)
        if not isinstance(target_path_item, dict):
            target_path_item = {}
            original_paths[str(path_key)] = target_path_item
        # 回写 path item 级 ``parameters``（如有）。
        expanded_path_item_params = path_item.get("parameters")
        if expanded_path_item_params is not None:
            target_path_item["parameters"] = expanded_path_item_params
        # 回写各 operation 级 ``parameters``（``requestBody`` 不写回）。
        for method_key, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            expanded_params = operation.get("parameters")
            if expanded_params is None:
                continue
            target_operation = target_path_item.get(method_key)
            if isinstance(target_operation, dict):
                # 操作已存在（如有 ``summary``、``description`` 等），只覆盖 ``parameters``。
                target_operation["parameters"] = expanded_params
            else:
                # 操作是合成 spec 临时加的（method 没在原 spec 里出现），新建一个最小 dict。
                target_path_item[str(method_key)] = {"parameters": expanded_params}

    # ---- 第 4 步：抽离展开后的 requestBody 到 map ----
    # expanded 操作中的 ``requestBody`` 是 jsonref 展开后的 dict；按 (path, method_upper) 收集。
    request_body_map: dict[tuple[str, str], dict[str, Any]] = {}
    expanded_paths_dict = expanded_paths if isinstance(expanded_paths, dict) else {}
    for path_key, path_item in expanded_paths_dict.items():
        if not isinstance(path_item, dict):
            continue
        for method_key, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            expanded_request_body = operation.get("requestBody")
            if expanded_request_body is None:
                continue
            request_body_map[(str(path_key), str(method_key).upper())] = expanded_request_body

    return raw_spec, request_body_map
