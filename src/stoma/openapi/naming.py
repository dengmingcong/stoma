"""OpenAPI 命名工具。

为 parser 与 renderer 共享 snake_case / PascalCase / 字段名转换函数。
提取为独立模块，避免互相依赖时出现循环 import。

- :func:`is_snake_case`：判断字符串是否已经是合法 snake_case。
- :func:`to_field_name`：将任意 OpenAPI 参数名转为合法 snake_case 字段名。
- :func:`to_pascal_case`：将 operationId 转换为 PascalCase 类名。
"""

from __future__ import annotations

import keyword
import re

from pydantic.alias_generators import to_snake


def is_snake_case(name: str) -> bool:
    """检测 name 是否已经是合法的 snake_case（且不是 Python 关键字）。

    :param name: 待检测字符串。
    :return: 合法的 snake_case 且非 Python 关键字时返回 ``True``，否则返回 ``False``。
    """
    if not name:
        return False
    if keyword.iskeyword(name):
        return False
    return bool(re.fullmatch(r"[a-z][a-z0-9_]*", name))


def to_field_name(name: str) -> str:
    """将 OpenAPI 参数名转为合法的 snake_case 字段名。

    处理 hyphen / 数字开头 / Python 关键字等边界 case：替换非字母数字下划线
    字符为 ``_``、合并连续下划线、剥离首尾下划线，空结果兜底为 ``"param"``；
    数字开头时前缀 ``n_``；命中关键字时前缀 ``p_``；最后用
    :func:`pydantic.alias_generators.to_snake` 把 CamelCase 拆为 snake_case。

    :param name: 原始 OpenAPI 参数名。
    :return: 转换后的 snake_case 字段名。
    """
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", name)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_") or "param"
    if cleaned[0].isdigit():
        cleaned = f"n_{cleaned}"
    if keyword.iskeyword(cleaned):
        cleaned = f"p_{cleaned}"
    return to_snake(cleaned)


def to_pascal_case(operation_id: str) -> str:
    """将 operationId 转换为 PascalCase 类名。

    把 hyphen / underscore 拆词，再按 CamelCase 边界（``[a-z0-9]`` 后跟
    ``[A-Z]``）二次切分，最后每个词首字母大写拼接。

    :param operation_id: OpenAPI ``operationId`` 字符串。
    :return: PascalCase 类名（可能为空串，当 ``operation_id`` 拆词后无有效词时）。
    """
    normalized = operation_id.replace("-", "_")
    words = re.split(r"[_-]+|(?<=[a-z0-9])(?=[A-Z])", normalized)
    return "".join(word.capitalize() for word in words if word)
