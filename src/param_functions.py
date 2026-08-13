"""参数标记的可调用入口。

此模块对外暴露 5 个工厂函数 ``Path / Query / Header / Body / Form``，
作为用户调用 ``Path()`` / ``Form()`` 等时的可见入口。
它们内部直接实例化 ``src.params`` 中的同名类，保持类的内部逻辑不变。

这样做的目的是把用户入口与类实现解耦：

- 用户代码统一 ``from src import Form, ...``
- 内部 ``src.params`` 可以自由重构（重命名类、调整 ``__init__`` 签名等）
- ``Param`` / ``ParamTypes`` 这类内部符号不在此暴露

每个函数的参数与对应类 ``__init__`` 完全一致；返回值是对应类的实例。
"""

from src.params import Body as _Body
from src.params import Form as _Form
from src.params import Header as _Header
from src.params import Path as _Path
from src.params import Query as _Query


def Path() -> _Path:  # noqa: N802
    """创建路径参数标记实例。

    :return: ``src.params.Path`` 实例。
    """
    return _Path()


def Query() -> _Query:  # noqa: N802
    """创建查询参数标记实例。

    :return: ``src.params.Query`` 实例。
    """
    return _Query()


def Header() -> _Header:  # noqa: N802
    """创建请求头参数标记实例。

    :return: ``src.params.Header`` 实例。
    """
    return _Header()


def Body(embed: bool = False, media_type: str | None = None) -> _Body:  # noqa: N802
    """创建请求体参数标记实例。

    :param embed: 是否嵌入单个字段。

        - 仅当只有 1 个 body 参数时有效。
        - ``embed=True`` → 用字段 alias 嵌入到顶层 ``{alias: value}``。
        - ``embed=False``（默认）→ 直接返回字段值（BaseModel 走 ``model_dump()`` 平展为顶层字段；scalar 走裸值）。
        - 多 body 参数时 ``embed`` 被忽略：始终按字段 alias 独立嵌入。

    :param media_type: Content-Type 请求头值。

        - 仅当同时满足以下三个条件时生效：

          1. 只有 1 个 body 参数；
          2. ``embed=False``；
          3. 参数类型是 scalar（非 BaseModel / 非 Mapping / 非序列 / 非 dataclass）。

        - 任一条件不满足时静默忽略。
        - ``None``（默认）= 让 Playwright 自动决定 Content-Type。

    :return: ``src.params.Body`` 实例。
    """
    return _Body(embed=embed, media_type=media_type)


def Form() -> _Form:  # noqa: N802
    """创建表单参数标记实例。

    返回实例的 ``kind`` 属性默认为 ``"scalar"``，由 ``src.routing`` 在分类阶段
    根据字段注解改写为 ``"scalar"`` 或 ``"list"``。

    :return: ``src.params.Form`` 实例。
    """
    return _Form()


__all__ = ["Body", "Form", "Header", "Path", "Query"]
