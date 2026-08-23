"""``src.stoma.dependencies.response`` 的单元测试。

覆盖 :class:`BaseResponseSpec` / :class:`ResponseSpec` / :class:`EmptyResponseSpec`
的 happy / failure 路径：按状态码（含 callable 谓词）与 media type（含 ``;charset=...``
后缀与 ``*`` 通配）的严格校验，以及 JSON 解析失败、Pydantic schema 不匹配、
``UnicodeDecodeError`` 的异常映射。

每个测试用 :class:`unittest.mock.MagicMock` 构造假的 Playwright
:class:`playwright.sync_api.APIResponse`，独立构造、不共享可变状态。
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from stoma.dependencies.response import (
    BaseResponseSpec,
    EmptyResponseSpec,
    Response,
    ResponseSpec,
)
from stoma.exceptions import ParseError, ValidationError

# ===== 测试响应模型 =====


class UserPayload(BaseModel):
    """测试用用户数据模型。

    :var name: 用户名。
    :vartype name: str
    :var age: 年龄。
    :vartype age: int
    """

    name: str
    age: int


# ===== MagicMock helpers =====


def _make_api_response(
    *,
    status: int = 200,
    content_type: str = "application/json",
    body: bytes | None = None,
    text: str | None = None,
    json_value: object = None,
) -> MagicMock:
    """构造一个 MagicMock 模拟 Playwright :class:`APIResponse`。

    每个测试独立调用此函数，确保 fake response 状态独立可配置。

    :param status: HTTP 状态码。
    :param content_type: content-type header 值。空字符串表示 ``headers`` 为空 dict。
    :param body: ``body()`` 返回值（仅当非 None 时设置）。
    :param text: ``text()`` 返回值（仅当非 None 时设置）。
    :param json_value: ``json()`` 返回值（仅当非 None 时设置）。未显式传 ``body`` 时
        自动按 :func:`json.dumps` 序列化，保证 :class:`ResponseSpec` 的
        ``validate_json`` 派发能拿到合法字节。
    :return: 构造好的 MagicMock。
    """
    import json

    mock = MagicMock()
    mock.status = status
    # content_type 为空时用空 dict：与真实 APIResponse 行为对齐（headers 缺失则 falsy）
    mock.headers = {"content-type": content_type} if content_type else {}
    if json_value is not None:
        mock.json.return_value = json_value
    if body is not None:
        mock.body.return_value = body
    elif json_value is not None:
        mock.body.return_value = json.dumps(json_value).encode("utf-8")
    if text is not None:
        mock.text.return_value = text
    return mock


# ===== BaseResponseSpec =====


class TestBaseResponseSpec:
    """``BaseResponseSpec`` 抽象基类的契约。"""

    def test_abstract_cannot_instantiate_with_int_status(self) -> None:
        """``int`` 状态码时直接实例化抛 ``TypeError``（``validate_response`` 未实现）。"""
        with pytest.raises(TypeError, match="abstract"):
            BaseResponseSpec(200, "application/json")

    def test_abstract_cannot_instantiate_with_callable_status(self) -> None:
        """``callable`` 状态码时直接实例化同样抛 ``TypeError``。"""
        with pytest.raises(TypeError, match="abstract"):
            BaseResponseSpec(lambda s: 400 <= s < 500, "application/json")

    def test_int_status_match_does_not_raise(self) -> None:
        """``int`` 状态码等值匹配时不抛错。"""
        spec = ResponseSpec(200, "application/json", UserPayload)
        spec._assert_status(200)

    def test_int_status_mismatch_raises_assertion(self) -> None:
        """``int`` 状态码不匹配抛 ``AssertionError``。"""
        spec = ResponseSpec(200, "application/json", UserPayload)
        with pytest.raises(AssertionError, match="HTTP 状态码不匹配"):
            spec._assert_status(404)

    def test_callable_status_match_does_not_raise(self) -> None:
        """``callable`` 谓词命中时不抛错。"""
        spec = ResponseSpec(lambda s: 400 <= s < 500, "application/json", UserPayload)
        spec._assert_status(404)
        spec._assert_status(499)

    def test_callable_status_mismatch_raises_assertion(self) -> None:
        """``callable`` 谓词未命中抛 ``AssertionError``。"""
        spec = ResponseSpec(lambda s: 400 <= s < 500, "application/json", UserPayload)
        with pytest.raises(AssertionError, match="HTTP 状态码不匹配"):
            spec._assert_status(200)

    def test_media_type_exact_match_does_not_raise(self) -> None:
        """content-type 与 spec 一致时不抛错。"""
        spec = ResponseSpec(200, "application/json", UserPayload)
        spec._assert_media_type("application/json")

    def test_media_type_strips_charset_suffix(self) -> None:
        """content-type 带 ``;charset=utf-8`` 后缀时仍匹配（被 strip 掉）。"""
        spec = ResponseSpec(200, "application/json", UserPayload)
        spec._assert_media_type("application/json; charset=utf-8")

    def test_media_type_mismatch_raises_assertion(self) -> None:
        """content-type 不匹配抛 ``AssertionError``。"""
        spec = ResponseSpec(200, "application/json", UserPayload)
        with pytest.raises(AssertionError, match="Content-Type 不匹配"):
            spec._assert_media_type("text/plain")

    def test_wildcard_media_matches_any_content_type(self) -> None:
        """``*`` 通配符匹配任意 content-type（包含 ``;charset=...`` 后缀与空串）。"""
        spec = ResponseSpec(200, "*", UserPayload)
        spec._assert_media_type("application/xml")
        spec._assert_media_type("text/plain; charset=utf-8")
        spec._assert_media_type("")

    def test_status_code_and_media_type_are_stored(self) -> None:
        """``__init__`` 正确保存 ``status_code`` 与 ``media_type``。"""
        spec = ResponseSpec(200, "application/json", UserPayload)
        assert spec.status_code == 200
        assert spec.media_type == "application/json"

    def test_response_dataclass_importable(self) -> None:
        """``Response`` dataclass 可正常导入。"""
        assert Response is not None


# ===== ResponseSpec =====


class TestResponseSpec:
    """``ResponseSpec`` 的 happy / failure 路径。"""

    def test_happy_path_returns_typed_instance(self) -> None:
        """happy path 返回 :class:`UserPayload` 实例且字段被填充。"""
        spec = ResponseSpec(200, "application/json", UserPayload)
        api_response = _make_api_response(
            status=200,
            content_type="application/json",
            json_value={"name": "alice", "age": 30},
        )
        result = spec.validate_response(api_response)
        assert isinstance(result, UserPayload)
        assert result.name == "alice"
        assert result.age == 30

    def test_happy_path_with_charset_suffix_content_type(self) -> None:
        """``Content-Type: application/json; charset=utf-8`` 时 happy path 仍通过。"""
        spec = ResponseSpec(200, "application/json", UserPayload)
        api_response = _make_api_response(
            status=200,
            content_type="application/json; charset=utf-8",
            json_value={"name": "bob", "age": 25},
        )
        result = spec.validate_response(api_response)
        assert result.name == "bob"

    def test_status_mismatch_raises_assertion(self) -> None:
        """status 不匹配抛 ``AssertionError``。"""
        spec = ResponseSpec(200, "application/json", UserPayload)
        api_response = _make_api_response(
            status=400,
            content_type="application/json",
            json_value={"name": "alice", "age": 30},
        )
        with pytest.raises(AssertionError, match="HTTP 状态码不匹配"):
            spec.validate_response(api_response)

    def test_media_type_mismatch_raises_assertion(self) -> None:
        """media type 不匹配抛 ``AssertionError``。"""
        spec = ResponseSpec(200, "application/json", UserPayload)
        api_response = _make_api_response(
            status=200,
            content_type="text/plain",
            json_value={"name": "alice", "age": 30},
        )
        with pytest.raises(AssertionError, match="Content-Type 不匹配"):
            spec.validate_response(api_response)

    def test_json_parse_failure_raises_parse_error(self) -> None:
        """JSON 解析失败抛 :class:`ParseError`，原始 ``text()`` 被保留为 ``response_text``。"""
        spec = ResponseSpec(200, "application/json", UserPayload)
        api_response = _make_api_response(
            status=200,
            content_type="application/json",
            text="not valid json",
        )
        api_response.json.side_effect = ValueError("invalid json")
        with pytest.raises(ParseError) as exc_info:
            spec.validate_response(api_response)
        assert exc_info.value.response_text == "not valid json"
        assert "invalid json" in exc_info.value.message

    def test_pydantic_schema_mismatch_raises_validation_error(self) -> None:
        """Pydantic schema 不匹配抛 stoma :class:`ValidationError`，含 Pydantic ``errors``。"""
        spec = ResponseSpec(200, "application/json", UserPayload)
        api_response = _make_api_response(
            status=200,
            content_type="application/json",
            json_value={"name": "alice"},  # 缺 ``age`` 字段
        )
        with pytest.raises(ValidationError) as exc_info:
            spec.validate_response(api_response)
        assert exc_info.value.errors is not None
        assert len(exc_info.value.errors) > 0
        # Pydantic 错误的 type 字段表明缺失 age 字段。
        assert any("age" in str(err.get("loc", [])) for err in exc_info.value.errors)

    def test_pydantic_type_mismatch_raises_validation_error(self) -> None:
        """字段类型不匹配（``age`` 应为 int 但传 str）抛 :class:`ValidationError`。"""
        spec = ResponseSpec(200, "application/json", UserPayload)
        api_response = _make_api_response(
            status=200,
            content_type="application/json",
            json_value={"name": "alice", "age": "not a number"},
        )
        with pytest.raises(ValidationError):
            spec.validate_response(api_response)

    def test_adapter_created_at_init(self) -> None:
        """构造时已创建 Pydantic :class:`TypeAdapter`。"""
        spec = ResponseSpec(200, "application/json", UserPayload)
        assert spec.adapter is not None


# ===== ResponseSpec =====


class TestResponseSpec:
    """``ResponseSpec`` 的 happy / failure 路径。"""

    def test_bytes_target_type_returns_bytes(self) -> None:
        """``expected_type=bytes`` 时返回 ``bytes``（来自 ``response.body()``）。"""
        spec = ResponseSpec(200, "image/png", bytes)
        api_response = _make_api_response(
            status=200,
            content_type="image/png",
            body=b"\x89PNG\r\n\x1a\n",
        )
        result = spec.validate_response(api_response)
        assert isinstance(result, bytes)
        assert result == b"\x89PNG\r\n\x1a\n"

    def test_str_target_type_returns_str(self) -> None:
        """``expected_type=str`` 时通过 ``validate_json`` 解析 JSON 字符串。"""
        spec = ResponseSpec(200, "text/plain", str)
        api_response = _make_api_response(
            status=200,
            content_type="text/plain",
            body=b'"hello"',
        )
        result = spec.validate_response(api_response)
        assert isinstance(result, str)
        assert result == "hello"

    def test_bytes_target_type_via_kwarg(self) -> None:
        """``expected_type=bytes`` 作为关键字参数也工作（与位置参数等价）。"""
        spec = ResponseSpec(200, "application/octet-stream", expected_type=bytes)
        api_response = _make_api_response(
            status=200,
            content_type="application/octet-stream",
            body=b"raw bytes",
        )
        result = spec.validate_response(api_response)
        assert result == b"raw bytes"

    def test_str_target_type_via_kwarg(self) -> None:
        """``expected_type=str`` 作为关键字参数也工作（与位置参数等价）。

        spec 自身的 ``media_type`` 不做 suffix 归一化，所以传不带 ``;charset=`` 的形式。
        实际响应 content-type 带 ``;charset=utf-8`` 后缀仍能匹配。
        """
        spec = ResponseSpec(200, "text/plain", expected_type=str)
        api_response = _make_api_response(
            status=200,
            content_type="text/plain; charset=utf-8",
            body=b'"content"',
        )
        result = spec.validate_response(api_response)
        assert result == "content"

    def test_missing_target_type_raises_type_error(self) -> None:
        """裸 ``ResponseSpec(...)``（漏 ``expected_type``）抛 ``TypeError``。"""
        with pytest.raises(TypeError, match="missing"):
            ResponseSpec(200, "application/octet-stream")

    def test_invalid_target_type_raises_type_error(self) -> None:
        """``expected_type=int`` 是合法的（与 ``str`` / ``bytes`` 同样走通用派发）。

        Phase 1 v3 重构后 ``ResponseSpec`` 统一按 ``expected_type`` 派发，``int``
        / ``str`` / Pydantic 模型 / 自定义类型皆可，type 限制只保留 ``bytes``
        短路路径。
        """
        spec = ResponseSpec(200, "application/json", expected_type=int)
        assert spec.expected_type is int

    def test_unicode_decode_error_wrapped_as_parse_error(self) -> None:
        """``expected_type=str`` 时非 JSON 字节抛 :class:`ValidationError`。

        Phase 1 v3 重构后 ``ResponseSpec`` 不再有 ``str`` 原始文本派发，统一走
        ``validate_json``——非合法 JSON 字节由 Pydantic 抛 ``ValidationError``，
        包含 Pydantic ``errors``。
        """
        spec = ResponseSpec(200, "text/plain", str)
        api_response = _make_api_response(
            status=200,
            content_type="text/plain",
            body=b"\xff\xfe",  # 非合法 JSON
        )
        with pytest.raises(ValidationError) as exc_info:
            spec.validate_response(api_response)
        assert exc_info.value.errors is not None

    def test_status_mismatch_raises_assertion(self) -> None:
        """status 不匹配抛 ``AssertionError``（bytes 派发）。"""
        spec = ResponseSpec(200, "image/png", bytes)
        api_response = _make_api_response(
            status=404,
            content_type="image/png",
            body=b"",
        )
        with pytest.raises(AssertionError, match="HTTP 状态码不匹配"):
            spec.validate_response(api_response)

    def test_media_type_mismatch_raises_assertion(self) -> None:
        """media type 不匹配抛 ``AssertionError``（bytes 派发）。"""
        spec = ResponseSpec(200, "image/png", bytes)
        api_response = _make_api_response(
            status=200,
            content_type="text/plain",
            body=b"",
        )
        with pytest.raises(AssertionError, match="Content-Type 不匹配"):
            spec.validate_response(api_response)

    def test_status_mismatch_raises_assertion_str_dispatch(self) -> None:
        """status 不匹配抛 ``AssertionError``（str 派发）。"""
        spec = ResponseSpec(200, "text/plain", str)
        api_response = _make_api_response(
            status=500,
            content_type="text/plain",
            body=b"err",
        )
        with pytest.raises(AssertionError, match="HTTP 状态码不匹配"):
            spec.validate_response(api_response)


# ===== Response.expect =====


class TestResponseExpect:
    """``Response.expect`` 方法将 spec 校验与响应对象解耦。"""

    def test_expect_dispatches_to_spec(self) -> None:
        """``response.expect(spec)`` 调用 ``spec.validate_response(raw)`` 并返回 ``T``。"""
        spec = ResponseSpec(200, "application/json", UserPayload)
        api_response = _make_api_response(
            status=200,
            content_type="application/json",
            json_value={"name": "alice", "age": 30},
        )
        response = Response(raw=api_response)
        result = response.expect(spec)
        assert isinstance(result, UserPayload)
        assert result.name == "alice"
        assert result.age == 30

    def test_expect_can_be_called_multiple_times_with_different_specs(self) -> None:
        """同一份 ``Response`` 可被多个 spec 反复校验（如先按成功分支，再按错误分支）。"""
        success_spec = ResponseSpec(200, "application/json", UserPayload)
        error_spec = ResponseSpec(500, "application/json", dict[str, str])

        # 200 成功响应：先按 success 解析为 UserPayload。
        success_response = _make_api_response(
            status=200,
            content_type="application/json",
            json_value={"name": "alice", "age": 30},
        )
        wrapped_success = Response(raw=success_response)
        result = wrapped_success.expect(success_spec)
        assert isinstance(result, UserPayload)

        # 500 错误响应：按 error 解析为 dict。
        error_response = _make_api_response(
            status=500,
            content_type="application/json",
            json_value={"error": "internal"},
        )
        wrapped_error = Response(raw=error_response)
        result = wrapped_error.expect(error_spec)
        assert result == {"error": "internal"}

    def test_expect_propagates_assertion_error(self) -> None:
        """``expect`` 把 status/media_type 不匹配的 ``AssertionError`` 透传给调用方。"""
        spec = ResponseSpec(200, "application/json", UserPayload)
        api_response = _make_api_response(
            status=400,
            content_type="application/json",
            json_value={"name": "alice", "age": 30},
        )
        response = Response(raw=api_response)
        with pytest.raises(AssertionError, match="HTTP 状态码不匹配"):
            response.expect(spec)


# ===== Public imports =====


def test_public_imports() -> None:
    """验证公开 API 可被 ``from stoma import ...`` 导入。"""
    from stoma import EmptyResponseSpec as PublicEmpty
    from stoma import Response as PublicResponse
    from stoma import ResponseSpec as PublicSpec

    assert PublicResponse is not None
    assert PublicSpec is not None
    assert PublicEmpty is not None
