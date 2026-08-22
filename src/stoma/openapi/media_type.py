"""OpenAPI / HTTP media type 判定工具。

集中 JSON content type 判定与 media type 字符串清洗：
- :func:`is_json_media_type` — 检查 media type 是否属于 JSON 家族
  （``application/json`` + ``application/*+json`` 后缀，如
  ``application/problem+json``、``application/json-patch+json``）。
  接受可能带 ``;charset=...`` 后缀的 content-type header（先 strip 再判断）。
- :func:`sanitize_media_type` — 将 media type 字符串转换为合法 Python
  标识符片段（用于在 renderer 中作为多 media type 区分的属性名后缀）。
  链式替换 ``/``、``+``、``-``、``.``、``;``、空格 为 ``_``，其中 ``+``
  替换为 ``_plus_`` 以保留语义可读性。
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


def sanitize_media_type(media_type: str) -> str:
    """将 media type 字符串清洗为合法 Python 标识符片段。

    链式执行以下替换（顺序固定，保证确定性输出）：
    1. ``lower()`` 归一化大小写。
    2. ``/`` → ``_``，分隔 type/subtype。
    3. ``+`` → ``_plus_``，保留 RFC 6839 structured syntax suffix 语义。
    4. ``-`` → ``_``，如 ``json-patch+json`` → ``json_patch_plus_json``。
    5. ``.`` → ``_``，如 ``vnd.api+json`` → ``vnd_api_plus_json``。
    6. ``;`` → ``_``，剥离 ``;charset=...`` 等参数分隔符。
    7. 空格 → ``_``，处理 ``text/xml; charset=utf-8`` 这种带空格形式
       （``;`` 与空格都产生 ``_``，因此中间出现连续两个下划线）。

    函数为纯字符串变换，无副作用，对相同输入总是返回相同结果。

    :param media_type: 原始 media type 字符串，可能带 ``;charset=...``
        后缀、混合大小写或含 ``+``、``-``、``.`` 等字符。
    :return: 可直接用作 Python 标识符的清洗后字符串。
    """
    return (
        media_type.lower()
        .replace("/", "_")
        .replace("+", "_plus_")
        .replace("-", "_")
        .replace(".", "_")
        .replace(";", "_")
        .replace(" ", "_")
    )


__all__ = ["is_json_media_type", "sanitize_media_type"]
