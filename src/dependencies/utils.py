"""参数依赖分析工具函数。"""

from collections.abc import Mapping
from dataclasses import is_dataclass
from types import UnionType  # Python 3.10+
from typing import Annotated, Any, Union, get_args, get_origin

from pydantic import BaseModel


def _lenient_issubclass(cls: Any, class_or_tuple: type | tuple[type, ...]) -> bool:
    """宽松的 issubclass 检查，避免对泛型类型报错。"""
    try:
        return isinstance(cls, type) and issubclass(cls, class_or_tuple)
    except TypeError:
        return False


def _is_sequence_type(annotation: Any) -> bool:
    """检查是否是序列类型（不包括 str/bytes）。"""
    return _lenient_issubclass(annotation, (list, set, tuple, frozenset))


def _annotation_is_complex(annotation: Any) -> bool:
    """检查基础类型是否是复杂类型。"""
    return (
        _lenient_issubclass(annotation, (BaseModel, Mapping))
        or _is_sequence_type(annotation)
        or is_dataclass(annotation)
    )


def field_annotation_is_complex(annotation: Any) -> bool:
    """检查是否是复杂类型（应为请求体）。

    参考 FastAPI 的 field_annotation_is_complex 逻辑：
    https://github.com/tiangolo/fastapi/blob/master/fastapi/_compat/shared.py

    复杂类型包括：
    - BaseModel 子类
    - Mapping（dict 等）
    - 序列（list、set 等）
    - dataclass
    - Union 中任一类型是复杂类型
    """
    origin = get_origin(annotation)

    if origin is Union or origin is UnionType:
        return any(field_annotation_is_complex(arg) for arg in get_args(annotation))

    if origin is Annotated:
        return field_annotation_is_complex(get_args(annotation)[0])

    return (
        _annotation_is_complex(annotation)
        or _annotation_is_complex(origin)
        or hasattr(origin, "__pydantic_core_schema__")
        or hasattr(origin, "__get_pydantic_core_schema__")
    )
