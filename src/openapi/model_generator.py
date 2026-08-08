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
from typing import TYPE_CHECKING, Any

import jsonref
from datamodel_code_generator import (
    InputFileType,
    OpenAPIScope,
    PythonVersion,
    generate,
)
from datamodel_code_generator.enums import DataModelType

# ``OpenAPISchemaError`` 定义在 :mod:`src.openapi.parser`，而
# :func:`parser.make_openapi_parser` 后续会反过来调用本模块
# 的 :func:`_expand_parameter_refs`，因此运行时 ``import`` 必须延迟到
# 函数内部，模块顶层只用 ``TYPE_CHECKING`` 给静态检查器提供类型。
if TYPE_CHECKING:  # pragma: no cover
    from src.openapi.parser import OpenAPISchemaError  # noqa: F401

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


def _expand_parameter_refs(raw_spec: dict[str, Any]) -> dict[str, Any]:
    """在 ``raw_spec`` 内仅展开 ``paths[*]`` 下 ``parameters`` 中的 ``$ref``。

    OpenAPI 允许 ``parameters`` 出现在两个层级：
    path item 级（直接挂在 ``paths[/x]`` 上，对该路径下所有 operation 生效）
    和 operation 级（挂在 ``paths[/x][<method>]`` 上）。两者都会被纳入合成规范
    并展开，而 ``requestBody``、``responses``、``summary``、``description``、``security`` 等键被丢弃，
    原样附带 ``components``，交给 :func:`jsonref.replace_refs` 立即解析。
    ``requestBody`` 和 ``responses`` 中的 ``$ref`` 字符串因此原封不动地留在
    原 ``raw_spec`` 中——datamodel-code-generator 会自行处理它们。

    解析结果以 path item 和 method 两个维度回写到 ``raw_spec``：
    path item 级 ``parameters`` 直接落到 ``raw_spec["paths"][<path>]["parameters"]``，
    operation 级 ``parameters`` 落到对应方法上；其余字段保持不变。
    ``jsonref.JsonRefError``（例如指向外部文件且无法解析的 ``$ref``）
    会被包装为 :class:`OpenAPISchemaError` 抛出。

    :param raw_spec: 待修改的 OpenAPI 规范字典（会被就地修改）。
    :return: 修改后的 ``raw_spec``。
    :raise OpenAPISchemaError: ``jsonref`` 解析参数 ``$ref`` 失败。
    """
    original_paths = raw_spec.get("paths")
    if not isinstance(original_paths, dict):
        original_paths = {}
        raw_spec["paths"] = original_paths

    synthetic_paths: dict[str, Any] = {}
    for path_key, path_item in original_paths.items():
        if not isinstance(path_item, dict):
            continue
        filtered_item: dict[str, Any] = {}
        if "parameters" in path_item:
            filtered_item["parameters"] = path_item["parameters"]
        for method_key, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            if "parameters" in operation:
                filtered_item[str(method_key)] = {"parameters": operation["parameters"]}
        if filtered_item:
            synthetic_paths[str(path_key)] = filtered_item

    synthetic: dict[str, Any] = {
        "paths": synthetic_paths,
        "components": raw_spec.get("components", {}),
    }

    try:
        expanded = jsonref.replace_refs(synthetic, proxies=False, lazy_load=False)
    except jsonref.JsonRefError as exc:
        from src.openapi.parser import OpenAPISchemaError

        msg = f"Failed to resolve parameter $ref: {exc}"
        raise OpenAPISchemaError(msg) from exc

    expanded_paths: object = expanded["paths"] if isinstance(expanded, dict) else {}
    if not isinstance(expanded_paths, dict):
        expanded_paths = {}

    for path_key, path_item in expanded_paths.items():
        if not isinstance(path_item, dict):
            continue
        target_path_item = original_paths.get(path_key)
        if not isinstance(target_path_item, dict):
            target_path_item = {}
            original_paths[str(path_key)] = target_path_item
        expanded_path_item_params = path_item.get("parameters")
        if expanded_path_item_params is not None:
            target_path_item["parameters"] = expanded_path_item_params
        for method_key, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            expanded_params = operation.get("parameters")
            if expanded_params is None:
                continue
            target_operation = target_path_item.get(method_key)
            if isinstance(target_operation, dict):
                target_operation["parameters"] = expanded_params
            else:
                target_path_item[str(method_key)] = {"parameters": expanded_params}

    return raw_spec
