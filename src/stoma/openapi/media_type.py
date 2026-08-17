"""OpenAPI / HTTP media type 判定工具。

集中 JSON content type 判定：
- :func:`is_json_media_type` — 检查 media type 是否属于 JSON 家族
  （``application/json`` + ``application/*+json`` 后缀，如
  ``application/problem+json``、``application/json-patch+json``）。
  接受可能带 ``;charset=...`` 后缀的 content-type header（先 strip 再判断）。
"""

from __future__ import annotations


def is_json_media_type(media_type: str) -> bool:
    """检查 media type 是否属于 JSON 家族。

    匹配：
    - 精确 ``application/json``
    - ``application/*+json`` 后缀（RFC 6839 structured syntax suffix，
      如 ``application/problem+json``、``application/json-patch+json``）

    支持 content-type header 直接传入：先 strip ``;charset=...`` 等参数，
    再做判断。空字符串返回 False。

    :param media_type: media type 字符串，可能带 ``;charset=...`` 后缀。
    :return: 是 JSON content type 返回 True，否则 False。
    """
    if not media_type:
        return False
    # strip ;charset=... 等参数
    main = media_type.split(";", 1)[0].strip().lower()
    return main == "application/json" or main.endswith("+json")


__all__ = ["is_json_media_type"]
