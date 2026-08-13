"""参数依赖分析工具函数。"""

from collections.abc import Mapping
from dataclasses import is_dataclass
from types import UnionType  # Python 3.10+
from typing import Annotated, Any, Union, get_args, get_origin

from pydantic import BaseModel

from src import UploadFile


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


def validate_binary_body_annotation(annotation: Any, *, field_name: str) -> None:
    """校验注解是否为 binary-body 模式的合法 UploadFile 字段，非法时抛 ``ValueError``。

    binary-body 模式仅接受以下形式：

    - ``UploadFile``
    - ``UploadFile | None`` / ``Optional[UploadFile]``

    不接受（由其他校验处理）：

    - ``list[UploadFile]`` —— binary-body 只支持单文件
    - ``Annotated[UploadFile, Form()]`` —— 已被 multipart 路径接管
    - 任意层 ``Union[UploadFile, str]`` —— 多语义冲突

    Pydantic v2 在 ``APIRoute._get_dependant`` 中获取的 ``field_info.annotation``
    已被 strip 掉 ``Annotated`` 包装，所以本函数不需要处理 Annotated。

    :param annotation: 待检查的类型注解。
    :param field_name: 字段名，用于错误信息中定位。
    :raise ValueError: 当注解不是合法的 binary-body UploadFile 字段类型。
    """
    if annotation is UploadFile:
        return
    origin = get_origin(annotation)
    if origin is Union or origin is UnionType:
        args = get_args(annotation)
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == 1 and non_none_args[0] is UploadFile:
            return
    msg = (
        f"upload_as_multipart=False 时 UploadFile 字段必须是裸 UploadFile"
        f"或 UploadFile | None（不能是 list/Form 包装），"
        f"字段 {field_name!r} 的注解是 {annotation!r}"
    )
    raise ValueError(msg)


# Playwright ``FormDataValue`` 支持的标量类型集合。
# bytes 不在其中（见 ``src.client._fill_form_field`` 的运行时检查），
# 因此 Form 不再接受 ``bytes`` / ``list[bytes]`` 字段。
_PLAYWRIGHT_FORM_SCALAR_TYPES: tuple[type, ...] = (str, int, float, bool)


def validate_form_field_annotation(annotation: Any) -> None:
    """校验 Form 字段注解是否合法，非法时抛 ``ValueError``。

    本函数在 ``src.routing`` 分类阶段被调用一次（每个 Form 字段一次），
    校验通过后无需保留任何运行时状态 —— ``src.client`` 直接基于
    ``field_info.annotation`` 自行判断 dispatch 路径，不再依赖 ``Form.kind`` 缓存。

    Pydantic 行为实测：在 ``APIRoute._get_dependant`` 中通过
    ``field_info.annotation`` 获取的注解是 Pydantic 处理后的实际类型，
    不再包含 ``Annotated`` 包装（即 ``Annotated[str, Form()]`` 的
    ``field_info.annotation`` 等于 ``str``）。因此本函数不再递归解 ``Annotated``，
    只需处理 ``Union`` / ``Optional`` / ``list`` 三种剩余包装。

    支持以下形式（兼容 PEP 604 与 ``typing.Optional`` 写法）：

    - 标量类型：``str`` / ``int`` / ``float`` / ``bool``
    - 标量列表：``list[str]`` / ``list[int]`` / ``list[float]`` / ``list[bool]``
    - 可选标量：``str | None`` / ``Optional[str]``
    - 可选标量列表：``list[str] | None`` / ``Optional[list[str]]``
    - 任意层 ``Union[X | None, ...]``（所有非 None 成员都必须是标量或 list[标量]）

    明确抛错的形式（语义不属于 Form 标量）：

    - ``bytes`` / ``list[bytes]``：Playwright ``FormDataValue`` 不含 ``bytes``，
      如需发送二进制请自行 ``json.dumps`` 为 ``str`` 后传入。
    - 文件类型：``UploadFile`` / ``list[UploadFile]``（应直接使用，不加 ``Form()`` 标记）
    - 路径类型：``pathlib.Path`` / ``list[pathlib.Path]``
    - 复杂类型：``BaseModel`` / ``dict`` / ``dataclass``
    - 多类型并集：``Union[str, int]``（两个及以上非 None 标量类型混合）
    - 非标量列表：``list[BaseModel]`` / ``list[dict]``
    - bare ``list``（缺少 list 元素类型，无法推断 scalar/list）

    实现要点：递归解包 ``Union`` / ``Optional``，跳过 ``None`` 成员，
    对单一非 None 标量 / ``list[标量]`` 静默通过，对其他形式抛 ``ValueError``。

    :param annotation: 待校验的字段注解（已由 Pydantic 解开 ``Annotated``）。
    :raise ValueError: 当字段注解不是 Form 合法标量或 list[标量] 形式。
    """
    origin = get_origin(annotation)

    if origin is Union or origin is UnionType:
        args = get_args(annotation)
        non_none_args = [arg for arg in args if arg is not type(None)]
        if not non_none_args:
            msg = (
                "Form 不支持的字段类型：注解为 Union 但所有成员都是 None。"
                "Form 仅接受标量类型（str、int、float、bool）或其列表形式（list[str] 等），"
                "以及上述类型的可选形式（str | None、Optional[list[str]] 等）。"
                "如需上传文件，请直接使用 UploadFile / list[UploadFile]，不要加 Form() 标记。"
                "不支持 pathlib.Path 或 BaseModel 子类作为 Form 字段。"
            )
            raise ValueError(msg)
        if len(non_none_args) == 1:
            validate_form_field_annotation(non_none_args[0])
            return
        msg = (
            f"Form 不支持的字段类型：注解为 {annotation!r}，包含多个非 None 标量类型并集。"
            "Form 仅接受单一标量类型（str、int、float、bool）或其列表形式（list[str] 等），"
            "以及上述类型的可选形式（str | None、Optional[list[str]] 等）。"
            "如需上传文件，请直接使用 UploadFile / list[UploadFile]，不要加 Form() 标记。"
            "不支持 pathlib.Path 或 BaseModel 子类作为 Form 字段。"
        )
        raise ValueError(msg)

    if origin is list:
        args = get_args(annotation)
        if len(args) == 1 and args[0] in _PLAYWRIGHT_FORM_SCALAR_TYPES:
            return
        if len(args) == 1 and args[0] is bytes:
            msg = (
                f"Form 不支持的字段类型：注解为 {annotation!r}（list[bytes]）。"
                "Playwright FormDataValue 不含 bytes 类型；"
                "如需发送二进制数据，请自行 json.dumps 为 str 后传入（list[str]），"
                "或改用 UploadFile / list[UploadFile]（不要加 Form() 标记）。"
            )
            raise ValueError(msg)
        msg = (
            f"Form 不支持的字段类型：注解为 {annotation!r}，list 元素必须是 str / int / float / bool。"
            "Form 仅接受标量列表（list[str]、list[int] 等），"
            "以及上述形式的可选写法（list[str] | None、Optional[list[int]] 等）。"
            "如需上传文件，请直接使用 UploadFile / list[UploadFile]，不要加 Form() 标记。"
            "不支持 pathlib.Path 或 BaseModel 子类作为 Form 字段。"
        )
        raise ValueError(msg)

    if annotation is list:
        msg = (
            f"Form 不支持的字段类型：注解为 {annotation!r}（bare list 缺少元素类型）。"
            "Form 需要明确的 list[标量] 形式，如 list[str]、list[int] 等。"
        )
        raise ValueError(msg)

    if annotation is bytes:
        msg = (
            f"Form 不支持的字段类型：注解为 {annotation!r}（bytes）。"
            "Playwright FormDataValue 不含 bytes 类型；"
            "如需发送二进制数据，请自行 json.dumps 为 str 后传入（str 字段），"
            "或改用 UploadFile（不要加 Form() 标记）。"
        )
        raise ValueError(msg)

    if annotation in _PLAYWRIGHT_FORM_SCALAR_TYPES:
        return

    msg = (
        f"Form 不支持的字段类型：注解为 {annotation!r}。"
        "Form 仅接受标量类型（str、int、float、bool）或其列表形式（list[str] 等），"
        "以及上述类型的可选形式（str | None、Optional[list[str]] 等）。"
        "如需上传文件，请直接使用 UploadFile / list[UploadFile]，不要加 Form() 标记。"
        "不支持 pathlib.Path 或 BaseModel 子类作为 Form 字段。"
    )
    raise ValueError(msg)
