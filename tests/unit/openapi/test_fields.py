"""``src.stoma.openapi.fields`` 的单元测试。

覆盖 :mod:`src.stoma.openapi.fields` 新增的 docstring 渲染相关 helper 与改
返回类型的 5 个 builder。

所有测试以 pytest 风格编写（plain function / pytest class + ``self``，
不使用 ``unittest.TestCase``）。
"""

from __future__ import annotations

from openapi_pydantic.v3.v3_0 import Example

from stoma.openapi.fields import (
    build_field_docstring,
    build_field_value,
    build_form_field_line,
    build_param_field_line,
    build_scalar_body_line,
    escape_docstring_content,
    resolve_examples,
)
from stoma.openapi.models import FieldDecl


class TestEscapeDocstringContent:
    """测试 :func:`escape_docstring_content` 各分支。"""

    def test_none_returns_none(self) -> None:
        """``None`` 输入直接透传。"""
        assert escape_docstring_content(None) is None

    def test_triple_quote_escaped(self) -> None:
        """三引号序列被转义为反斜杠 + 三引号。"""
        assert escape_docstring_content('a"""b') == 'a\\"\\"\\"b'

    def test_backslash_escaped_before_triple_quote(self) -> None:
        """反斜杠先转义（避免后续重复转义三引号的反斜杠），再转义三引号。

        输入 ``\\\\\"\"\"`` 经过两次 replace：先反斜杠变双反斜杠，再三引号序列
        变 3 对反斜杠 + 引号。该顺序保证反斜杠不会被重复加反斜杠。
        """
        assert escape_docstring_content('\\"""') == '\\\\\\"\\"\\"'


class TestBuildFieldDocstring:
    """测试 :func:`build_field_docstring` 各分支（dmcg 1:1 复刻）。"""

    def test_none_or_blank_returns_none(self) -> None:
        """``None`` 与仅空白输入返回 ``None``，便于模板条件跳过。"""
        assert build_field_docstring(None) is None
        assert build_field_docstring("") is None
        assert build_field_docstring("   \n  ") is None

    def test_single_line_uses_inline_triple_quotes(self) -> None:
        """单行（无换行）走单行三引号格式。"""
        assert build_field_docstring("hello") == '"""hello"""'

    def test_multi_line_uses_indented_block(self) -> None:
        """多行模式每行缩进 4 空格（class body 默认）。"""
        assert build_field_docstring("hello\nworld") == '"""\n    hello\n    world\n    """'

    def test_ends_with_unescaped_quote_adds_escape(self) -> None:
        """单行文本以单个双引号结尾时自动加反斜杠转义，避免 docstring 被提前关闭。

        1:1 复刻 dmcg 0.72.2 ``format_docstring`` 的 ``_ends_with_unescaped_quote``
        安全网。
        """
        result = build_field_docstring('value="x"')
        # 末尾的 " 被自动加 \\ 转为 \\"，确保 docstring 完整闭合。
        assert result == '"""value="x\\""""'


class TestBuildFieldValue:
    """测试 :func:`build_field_value` 的 example 优先级（dmcg 1:1）。"""

    def test_description_only(self) -> None:
        """仅有 description 时只渲染 description 段。"""
        assert build_field_value("用户 ID") == "用户 ID"

    def test_single_example_renders_example_line(self) -> None:
        """单值 example 渲染为 ``Example: {example!r}``。"""
        assert build_field_value("用户 ID", example=42) == "用户 ID\n\nExample: 42"

    def test_plural_examples_render_bullet_list(self) -> None:
        """``examples`` 列表 >= 2 项时渲染项目符号列表，前缀 ``Examples:``。"""
        assert build_field_value("状态码", examples=[200, 404, 500]) == "状态码\n\nExamples:\n- 200\n- 404\n- 500"


class TestResolveExamples:
    """测试 :func:`resolve_examples` 对 OpenAPI ``Example`` 对象的 unwrap。"""

    def test_dict_values_unwrapped_from_example(self) -> None:
        """``dict[str, Example]`` 输入逐个 unwrap ``.value``。"""
        ex1 = Example(value="foo")
        ex2 = Example(value="bar")
        assert resolve_examples(examples={"first": ex1, "second": ex2}) == ["foo", "bar"]

    def test_single_example_object(self) -> None:
        """单个 ``Example`` 对象作为 ``examples`` 时 unwrap 后返回单元素列表。"""
        assert resolve_examples(examples=Example(value="hello")) == ["hello"]


class TestBuildersReturnFieldDecl:
    """测试 builder 改返回类型后仍为 :class:`FieldDecl` 且 docstring 正常拼接。"""

    def test_build_param_field_line_returns_field_decl(self) -> None:
        """``build_param_field_line`` 返回 ``FieldDecl``，无 description 时 docstring 为 ``None``。"""
        decl = build_param_field_line("q", "str", True, "query")
        assert isinstance(decl, FieldDecl)
        assert decl.line == "q: str"
        assert decl.docstring is None

    def test_build_form_field_line_with_docstring(self) -> None:
        """``build_form_field_line`` 含 description 时返回 ``FieldDecl`` 带单行 docstring。"""
        decl = build_form_field_line("user_id", "str", description="用户 ID")
        assert isinstance(decl, FieldDecl)
        assert decl.line == "user_id: Annotated[str, Form()]"
        assert decl.docstring == '"""用户 ID"""'

    def test_build_scalar_body_line_with_plural_examples(self) -> None:
        """``build_scalar_body_line`` 接受 4 个 keyword-only 形参，examples 多值时渲染 bullet 列表。"""
        decl = build_scalar_body_line(
            "int",
            "application/json",
            description="计数",
            examples=[1, 2, 3],
        )
        assert isinstance(decl, FieldDecl)
        assert decl.line == "body: Annotated[int, Body(media_type='application/json')]"
        assert decl.docstring is not None
        assert "Examples:" in decl.docstring
        assert "- 1" in decl.docstring
        assert "- 2" in decl.docstring
        assert "- 3" in decl.docstring
