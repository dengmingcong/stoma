"""Pydantic 字段声明字符串构造。

- :func:`resolve_array_type` — ``type: array`` 派生 ``list[<T>]`` 字符串。
- :func:`escape_docstring_content` — 转义 description 中的反斜杠与三引号。
- :func:`build_field_docstring` — 复刻 dmcg ``format_docstring`` 的输出格式。
- :func:`resolve_examples` — 归一化 OpenAPI ``example`` / ``examples`` 为扁平值列表。
- :func:`build_field_value` — 拼接 description + example(s) docstring body。
- :func:`build_form_field_line` — form 标量字段声明（含 snake_case 边界处理）。
- :func:`build_upload_file_field_line` — multipart file 字段声明。
- :func:`build_param_field_line` — query / path / header 参数字段声明（8 种分支形态）。
- :func:`build_scalar_body_line` — primitive body 字段声明。
- :func:`build_endpoint_docstring` — endpoint 模块 docstring 和类 docstring 字符串。

所有 builder（``build_*_line``）返回 :class:`stoma.openapi.models.FieldDecl`，
``line`` 是字段声明字符串，``docstring`` 是 dmcg 1:1 风格的字段 docstring
（无 description / example 时为 ``None``）。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from stoma.openapi.models import FieldDecl
from stoma.openapi.naming import is_snake_case, to_field_name
from stoma.openapi.type_mapping import python_type_for_array_items


def resolve_array_type(prop_schema: dict[str, Any]) -> str:
    """对 ``type: array`` 的 property 派生 ``list[<T>]`` 字符串。

    从 ``prop_schema["items"]`` 取元素信息，委托给
    :func:`src.openapi.type_mapping.python_type_for_array_items`。
    ``items`` 缺失或类型未命中映射时 fallback 到 ``"list[str]"``。

    :param prop_schema: property 的 schema 字典（含 ``type`` / ``items``）。
    :return: ``"list[<T>]"`` 形式的 Python 类型字符串。
    """
    items = prop_schema.get("items")
    return python_type_for_array_items(items)


def escape_docstring_content(value: str | None) -> str | None:
    r"""转义 ``value`` 中的反斜杠与三引号，避免 docstring 语法错误。

    处理：

    - 反斜杠：``\\`` → ``\\\\``（必须先转义，避免重复转义破坏后续 ``\"\"\"``）。
    - 三引号：``\"\"\"`` → ``\\\"\\\"\\\"``（会立即终止 docstring）。

    1:1 复刻 dmcg 0.72.2 ``model/base.py:149-165`` ``escape_docstring``。

    :param value: 待转义字符串，可为 ``None``。
    :return: 转义后的字符串；``None`` 直接透传。
    """
    if value is None:
        return None
    return value.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')


def _ends_with_unescaped_quote(value: str) -> bool:
    """判断 ``value`` 末尾是否有未转义的双引号。

    仅在 :func:`build_field_docstring` 单行分支调用，避免反斜杠转义双引号
    后再追加三引号时 docstring 被立即关闭。1:1 复刻 dmcg 0.72.2
    ``model/base.py:170-179``。

    :param value: 已转义的字符串。
    :return: 末尾双引号未转义时为 ``True``。
    """
    if not value.endswith('"'):
        return False

    backslash_count = 0
    for char in reversed(value[:-1]):
        if char != "\\":
            break
        backslash_count += 1
    return backslash_count % 2 == 0


def build_field_docstring(
    value: str | None,
    indent_spaces: int = 4,
    *,
    use_single_line: bool = True,
) -> str | None:
    r"""把 ``value`` 包装成符合 PEP 257 的 docstring 字符串。

    单行模式（无换行且 ``use_single_line=True``）输出单行三引号包裹的转义文本；
    多行模式（含换行或 ``use_single_line=False``）输出三引号包裹的多行文本，
    缩进固定 4 空格（class body 默认）。

    当 ``value`` 为空（``None`` 或仅空白）时返回 ``None``，便于模板条件跳过。
    1:1 复刻 dmcg 0.72.2 ``model/base.py:181-214`` ``format_docstring``。

    :param value: docstring 文本，可为 ``None``。
    :param indent_spaces: 多行模式每行（首行除外）的缩进空格数。
    :param use_single_line: 是否在文本无换行时使用单行三引号格式。
    :return: docstring 完整字符串（含三引号）；空输入返回 ``None``。
    """
    if value is None or not value.strip():
        return None

    escaped = escape_docstring_content(value) or ""

    if use_single_line and "\n" not in value and "\r" not in value:
        if _ends_with_unescaped_quote(escaped):
            escaped = f'{escaped[:-1]}\\"'
        return f'"""{escaped}"""'

    indent = max(indent_spaces, 0) * " "
    if indent:
        escaped = "\n".join(f"{indent}{line}" if line else "" for line in escaped.split("\n"))
        return f'"""\n{escaped}\n{indent}"""'
    return f'"""\n{escaped}\n"""'


def build_endpoint_docstring(
    summary: str | None,
    description: str | None,
    *,
    operation_id: str | None = None,
) -> str | None:
    r"""Build endpoint-level docstring (module docstring / class docstring).

    Logic:
    - Both summary and description present -> single-line summary + blank line +
      "Generated from OpenAPI: <operation_id>" + multi-line description.
    - Summary only -> single-line docstring with Chinese period.
    - Description only -> multi-line docstring, 4-space indent, no extra period.
    - Neither -> None (template skips rendering).

    operation_id is only rendered as second paragraph when docstring content exists.

    :param summary: OpenAPI summary, may be None.
    :param description: OpenAPI description, may be None.
    :param operation_id: OpenAPI operationId, optional (module docstring only).
    :return: Complete docstring string (with triple quotes); None when no content.
    """
    summary_str = summary.strip() if summary else ""
    description_str = description.strip() if description else ""

    if not summary_str and not description_str:
        return None

    if summary_str and description_str:
        op_id_line = f"Generated from OpenAPI: {operation_id}" if operation_id else None
        if op_id_line:
            return f'"""{summary_str}。\n\n{op_id_line}\n{description_str}\n"""'
        return f'"""{summary_str}。\n\n{description_str}\n"""'

    if description_str:
        op_id_line = f"Generated from OpenAPI: {operation_id}" if operation_id else None
        if op_id_line:
            return f'"""\n{op_id_line}\n{description_str}\n"""'
        return f'"""\n{description_str}\n"""'

    if summary_str:
        op_id_line = f"Generated from OpenAPI: {operation_id}" if operation_id else None
        if op_id_line:
            return f'"""{summary_str}。\n\n{op_id_line}\n"""'
        return f'"""{summary_str}。"""'

    msg = "unreachable: summary_str and description_str are both empty after line 145"
    raise AssertionError(msg)


def _unwrap_example(value: Any) -> Any:
    """若 ``value`` 是 OpenAPI ``Example`` 对象，返回 ``.value``；否则原样返回。

    通过 ``BaseModel`` + Pydantic v2 ``model_fields`` 检测 ``value`` 字段，
    避免对非 Example 的 BaseModel（如 :class:`openapi_pydantic.Reference`）
    误判。dict / 标量 / 缺失 ``.value`` 字段的对象都原样返回。

    :param value: 待 unwrap 的值。
    :return: unwrap 后的字面量值。
    """
    if isinstance(value, BaseModel) and "value" in type(value).model_fields:
        return value.value  # type: ignore[attr-defined]
    return value


def resolve_examples(
    example: Any | None = None,
    examples: Any | None = None,
) -> list[Any]:
    """归一化 OpenAPI ``example`` / ``examples`` 为扁平的字面量值列表。

    OpenAPI 3.0 / 3.1 中 ``examples`` 形态多样：

    - ``Dict[str, Example]``（3.0 / 3.1 标准）→ 取每个 value 的 ``Example.value``。
    - ``list[Any]``（3.1 JSON Schema 风格 ``examples``）→ 逐项 unwrap。
    - 单个 ``Example`` 对象 → ``[Example.value]``。
    - 单个标量 → ``[scalar]``。

    ``example`` 与 ``examples`` 都为 ``None`` 时返回空列表。

    :param example: 单值（任意类型，含 ``Example`` 对象）。
    :param examples: 多值（dict / list / ``Example`` / 标量）。
    :return: 扁平的字面量值列表。
    """
    if examples is not None:
        if isinstance(examples, dict):
            return [_unwrap_example(v) for v in examples.values()]
        if isinstance(examples, list):
            return [_unwrap_example(v) for v in examples]
        return [_unwrap_example(examples)]
    if example is not None:
        return [_unwrap_example(example)]
    return []


def build_field_value(
    description: str | None,
    example: Any | None = None,
    examples: Any | None = None,
) -> str | None:
    """拼接 description + example(s) docstring body（不含三引号）。

    example 优先级与 dmcg 0.72.2 ``model/base.py:887-921`` ``docstring``
    property 完全一致：

    - ``examples`` 列表长度 > 1 → 项目符号列表 ``- {v!r}``（前缀 ``Examples:``）。
    - 单值 ``example`` → ``Example: {example!r}``。
    - ``examples`` 列表长度 == 1 → ``Example: {examples[0]!r}``。
    - 都没有 → 不渲染 example 段。

    description 始终在前（若有），与 example 段之间用空行分隔；最终
    ``description`` / ``example(s)`` 都不存在时返回 ``None``。

    :param description: OpenAPI description 文本，可为 ``None``。
    :param example: OpenAPI 单值 example，可为 ``None``。
    :param examples: OpenAPI 多值 examples（dict / list / ``Example`` / 标量）。
    :return: docstring body 字符串；``description`` 与 example 都没有时为 ``None``。
    """
    parts: list[str] = []
    if description is not None:
        parts.append(description)

    examples_list = resolve_examples(example=example, examples=examples)

    if len(examples_list) > 1:
        examples_str = "\n".join(f"- {v!r}" for v in examples_list)
        parts.append(f"Examples:\n{examples_str}")
    elif len(examples_list) == 1:
        parts.append(f"Example: {examples_list[0]!r}")

    if not parts:
        return None
    return "\n\n".join(parts)


def _wrap_field_decl(
    line: str,
    description: str | None,
    example: Any | None,
    examples: Any | None,
) -> FieldDecl:
    """为已有 line 字符串追加 dmcg 风格 docstring，返回 :class:`FieldDecl`。

    所有 builder 的最后一步：line 拼接逻辑保持原样，仅在末尾追加 docstring
    渲染。``description`` 与 example 都为空时 ``docstring`` 为 ``None``。

    :param line: 已构造的字段声明字符串。
    :param description: OpenAPI description 文本。
    :param example: OpenAPI 单值 example。
    :param examples: OpenAPI 多值 examples。
    :return: :class:`FieldDecl`，``docstring`` 可能为 ``None``。
    """
    body = build_field_value(description, example=example, examples=examples)
    docstring = build_field_docstring(body) if body else None
    return FieldDecl(line=line, docstring=docstring)


def build_form_field_line(
    name: str,
    py_type: str,
    *,
    description: str | None = None,
    example: Any | None = None,
    examples: Any | None = None,
) -> FieldDecl:
    """构造 form 字段声明字符串，含非 snake_case 自动 ``Field(serialization_alias=...)``。

    字段名走 :func:`openapi.naming.to_field_name` 处理 hyphen / 关键字 /
    数字开头等边界；若转换结果与原名不同（非合法 snake_case），追加
    ``Field(serialization_alias=<原名!r>)`` 让 FastAPI Form 提交时用原名，
    避免接口协议破坏（参考 :func:`build_param_field_line` 的非 snake_case 分支）。

    :param name: 原始 OpenAPI property 名称。
    :param py_type: Python 类型字符串。
    :param description: OpenAPI description，可为 ``None``。
    :param example: OpenAPI 单值 example，可为 ``None``。
    :param examples: OpenAPI 多值 examples，可为 ``None``。
    :return: :class:`FieldDecl`，``docstring`` 由 description / example(s) 派生。
    """
    field_name = to_field_name(name)
    if not is_snake_case(name):
        line = f"{field_name}: Annotated[{py_type}, Form(), Field(serialization_alias={name!r})]"
    else:
        line = f"{field_name}: Annotated[{py_type}, Form()]"
    return _wrap_field_decl(line, description, example, examples)


def build_upload_file_field_line(
    name: str,
    *,
    description: str | None = None,
    example: Any | None = None,
    examples: Any | None = None,
) -> FieldDecl:
    """构造 multipart file 字段声明字符串。

    ``name`` 非 snake_case 时追加 ``Field(serialization_alias=<origin>)``
    （与 form 标量字段一致——FastAPI Form / Playwright FormData 提交时用原名，
    避免接口协议破坏）。``name`` 已是 snake_case 时裸 ``UploadFile``。

    字段名同样走 :func:`openapi.naming.to_field_name` 处理边界
    （hyphen / 关键字 / 数字开头等）。

    :param name: 原始 OpenAPI property 名称。
    :param description: OpenAPI description，可为 ``None``。
    :param example: OpenAPI 单值 example，可为 ``None``。
    :param examples: OpenAPI 多值 examples，可为 ``None``。
    :return: :class:`FieldDecl`，``docstring`` 由 description / example(s) 派生。
    """
    field_name = to_field_name(name)
    if is_snake_case(name):
        line = f"{field_name}: UploadFile"
    else:
        line = f"{field_name}: Annotated[UploadFile, Field(serialization_alias={name!r})]"
    return _wrap_field_decl(line, description, example, examples)


def build_param_field_line(
    name: str,
    param_type: str,
    required: bool,
    location: str,
    *,
    description: str | None = None,
    example: Any | None = None,
    examples: Any | None = None,
) -> FieldDecl:
    """构建参数（query / path / header）字段声明字符串。

    使用 FastAPI 推荐的 ``Annotated[...]`` 形式：所有 metadata
    （``Header()`` / ``Field(serialization_alias=...)``）放进
    ``Annotated[...]`` 内，只在可选字段上保留 ``= None`` 默认值。

    八种分支形态：

    - header × required × snake: ``name: Annotated[T, Header()]``
    - header × required × non-snake:
      ``name: Annotated[T, Header(), Field(serialization_alias='X')]``
    - header × optional × snake:
      ``name: Annotated[T | None, Header()] = None``
    - header × optional × non-snake:
      ``name: Annotated[T | None, Header(), Field(serialization_alias='X')] = None``
    - query/path × required × snake: ``name: T``
    - query/path × required × non-snake:
      ``name: Annotated[T, Field(serialization_alias='X')]``
    - query/path × optional × snake: ``name: T | None = None``
    - query/path × optional × non-snake:
      ``name: Annotated[T | None, Field(serialization_alias='X')] = None``

    :param name: 原始 OpenAPI 参数名。
    :param param_type: Python 类型字符串。
    :param required: 是否必需。
    :param location: ``"header"`` / ``"query"`` / ``"path"``。
    :param description: OpenAPI description，可为 ``None``。
    :param example: OpenAPI 单值 example，可为 ``None``。
    :param examples: OpenAPI 多值 examples，可为 ``None``。
    :return: :class:`FieldDecl`，``docstring`` 由 description / example(s) 派生。
    """
    is_header = location == "header"
    is_snake = is_snake_case(name)
    field_name = name if is_snake else to_field_name(name)

    base_type = param_type if required or " | None" in param_type else f"{param_type} | None"

    metadata: list[str] = []
    if is_header:
        metadata.append("Header()")
    if not is_snake:
        metadata.append(f"Field(serialization_alias={name!r})")

    annotation = f"Annotated[{base_type}, {', '.join(metadata)}]" if metadata else base_type

    default = "" if required else " = None"
    line = f"{field_name}: {annotation}{default}"
    return _wrap_field_decl(line, description, example, examples)


def build_scalar_body_line(
    py_type: str,
    media_type: str,
    *,
    description: str | None = None,
    example: Any | None = None,
    examples: Any | None = None,
) -> FieldDecl:
    """构造 primitive schema 单字段 body 字段声明。

    渲染为 ``body: Annotated[<type>, Body(media_type=<media_type>)]``，
    wire 是裸值（``Body()`` 默认 ``embed=False``）。``media_type`` 嵌入
    ``Body(media_type=...)``，由 client 通过 ``param_info.media_type`` 派生
    Content-Type header（不走 Header field 路径）。

    既覆盖 ``application/json`` 标量路径，也覆盖兜底 RAW 路径
    （``text/plain`` / ``application/xml`` 等非 JSON / 非 form / 非 binary）。

    :param py_type: Python 类型字符串（如 ``"int"`` / ``"str"``）。
    :param media_type: 媒体类型字符串，嵌入 ``Body(media_type=...)``。
    :param description: OpenAPI description，可为 ``None``。
    :param example: OpenAPI 单值 example，可为 ``None``。
    :param examples: OpenAPI 多值 examples，可为 ``None``。
    :return: :class:`FieldDecl`，``docstring`` 由 description / example(s) 派生。
    """
    line = f"body: Annotated[{py_type}, Body(media_type={media_type!r})]"
    return _wrap_field_decl(line, description, example, examples)


__all__ = [
    "build_endpoint_docstring",
    "build_field_docstring",
    "build_field_value",
    "build_form_field_line",
    "build_param_field_line",
    "build_scalar_body_line",
    "build_upload_file_field_line",
    "escape_docstring_content",
    "resolve_array_type",
    "resolve_examples",
]
