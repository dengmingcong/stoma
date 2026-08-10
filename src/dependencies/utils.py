"""参数依赖分析工具函数。"""

from collections.abc import Mapping
from dataclasses import is_dataclass
from types import UnionType  # Python 3.10+
from typing import Annotated, Any, Union, get_args, get_origin

from pydantic import BaseModel

from src.params import UploadFile


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


def _is_uploadfile_or_list_annotation(annotation: Any) -> bool:
    """判断注解是否可识别为上传文件字段。

    支持以下形式（兼容 PEP 604 与 ``typing.Optional`` 写法）：

    - ``UploadFile``
    - ``list[UploadFile]``
    - ``UploadFile | None`` / ``Optional[UploadFile]``
    - ``list[UploadFile] | None`` / ``Optional[list[UploadFile]]``
    - 任意层 ``Union[UploadFile | None, list[UploadFile] | None]``（只要全部成员都是文件字段类型，则返回 True）

    明确不支持的形式（语义含糊，留给后续由用户在 ``Param`` 标记或运行时显式声明）：

    - ``Union[UploadFile, str]`` 等混入非文件类型 → 返回 False
    - 非 ``UploadFile`` / 非 ``list[UploadFile]`` 的任意类型 → 返回 False

    实现要点：递归解包 ``Union`` / ``Optional``，跳过 ``None`` 成员，
    要求每个非 ``None`` 成员都是 ``UploadFile`` 或 ``list[UploadFile]``。

    :param annotation: 待检查的类型注解。
    :return: 如果是合法的上传文件字段类型则返回 True。
    """
    origin = get_origin(annotation)
    if origin is Union or origin is UnionType:
        # ``Optional`` 上下文：跳过 ``None`` 成员后，剩余成员全部必须是文件字段类型。
        return all(
            arg is type(None) or _is_uploadfile_or_list_annotation(arg)
            for arg in get_args(annotation)
        )

    if annotation is UploadFile:
        return True

    if origin is list:
        args = get_args(annotation)
        return len(args) == 1 and args[0] is UploadFile

    return False
