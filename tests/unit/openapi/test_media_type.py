"""``is_json_media_type`` 与 ``sanitize_media_type`` 单元测试。"""

from __future__ import annotations

import pytest

from stoma.openapi.media_type import is_json_media_type, sanitize_media_type


class TestIsJsonMediaType:
    """``is_json_media_type`` 的各种 case。"""

    @pytest.mark.parametrize(
        "media_type",
        [
            "application/json",
            "application/json; charset=utf-8",
            "application/json;charset=utf-8",
            "APPLICATION/JSON",  # 大小写不敏感
            "  application/json  ",  # 前后空白
            "application/problem+json",
            "application/json-patch+json",
            "application/merge-patch+json",
            "application/vnd.api+json",
        ],
    )
    def test_json_family_returns_true(self, media_type: str) -> None:
        """JSON 家族（含 +json 后缀变体）都返回 True。"""
        assert is_json_media_type(media_type) is True

    @pytest.mark.parametrize(
        "media_type",
        [
            "text/plain",
            "application/octet-stream",
            "text/html",
            "application/xml",
            "multipart/form-data",
            "image/png",
            "application/x-www-form-urlencoded",
        ],
    )
    def test_non_json_returns_false(self, media_type: str) -> None:
        """非 JSON media type 返回 False。"""
        assert is_json_media_type(media_type) is False

    def test_empty_string_returns_false(self) -> None:
        """空字符串返回 False。"""
        assert is_json_media_type("") is False


class TestSanitizeMediaType:
    """``sanitize_media_type`` 的各种 case。"""

    @pytest.mark.parametrize(
        ("media_type", "expected"),
        [
            ("application/json", "application_json"),
            ("application/problem+json", "application_problem_plus_json"),
            ("text/xml; charset=utf-8", "text_xml__charset=utf_8"),
            ("image/png", "image_png"),
        ],
    )
    def test_basic_substitutions(self, media_type: str, expected: str) -> None:
        """常见 media type 按链式规则清洗。"""
        assert sanitize_media_type(media_type) == expected

    def test_empty_string_returns_empty(self) -> None:
        """空字符串返回空字符串。"""
        assert sanitize_media_type("") == ""

    def test_uppercase_normalized_to_lowercase(self) -> None:
        """大写字符经 ``lower()`` 归一化。"""
        assert sanitize_media_type("APPLICATION/JSON") == "application_json"

    def test_dash_dot_combinations(self) -> None:
        """``-`` 与 ``.`` 都替换为 ``_``，便于作为 Python 标识符。"""
        assert sanitize_media_type("application/vnd.api+json") == "application_vnd_api_plus_json"
        assert sanitize_media_type("application/json-patch+json") == "application_json_patch_plus_json"

    def test_plus_must_use_plus_marker_not_bare_underscore(self) -> None:
        """``+`` 替换为 ``_plus_``（非简单 ``_``），保留语义可读性。"""
        # 若退化为简单 "_"，则 "problem+json" 会与 "problem_json" 撞名，
        # 而原 media type 中前者含 RFC 6839 structured suffix，后者不含。
        assert "+" not in sanitize_media_type("application/problem+json")
        assert "plus" in sanitize_media_type("application/problem+json")

    def test_is_deterministic(self) -> None:
        """同一输入重复调用产生相同输出（纯函数，无副作用）。"""
        sample = "text/xml; charset=utf-8"
        first = sanitize_media_type(sample)
        second = sanitize_media_type(sample)
        third = sanitize_media_type(sample)
        assert first == second == third
