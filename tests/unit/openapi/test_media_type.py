"""``is_json_media_type`` 单元测试。"""

from __future__ import annotations

import pytest

from src.openapi.media_type import is_json_media_type


class TestIsJsonMediaType:
    """``is_json_media_type`` 的各种 case。"""

    @pytest.mark.parametrize("media_type", [
        "application/json",
        "application/json; charset=utf-8",
        "application/json;charset=utf-8",
        "APPLICATION/JSON",  # 大小写不敏感
        "  application/json  ",  # 前后空白
        "application/problem+json",
        "application/json-patch+json",
        "application/merge-patch+json",
        "application/vnd.api+json",
    ])
    def test_json_family_returns_true(self, media_type: str) -> None:
        """JSON 家族（含 +json 后缀变体）都返回 True。"""
        assert is_json_media_type(media_type) is True

    @pytest.mark.parametrize("media_type", [
        "text/plain",
        "application/octet-stream",
        "text/html",
        "application/xml",
        "multipart/form-data",
        "image/png",
        "application/x-www-form-urlencoded",
    ])
    def test_non_json_returns_false(self, media_type: str) -> None:
        """非 JSON media type 返回 False。"""
        assert is_json_media_type(media_type) is False

    def test_empty_string_returns_false(self) -> None:
        """空字符串返回 False。"""
        assert is_json_media_type("") is False
