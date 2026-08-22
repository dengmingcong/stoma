"""OpenAPI / HTTP media type 判定工具。

集中 JSON content type 判定与 media type 字符串清洗：
- :func:`is_json_media_type` — 检查 media type 是否属于 JSON 家族
  （``application/json`` + ``application/*+json`` 后缀，如
  ``application/problem+json``、``application/json-patch+json``）。
  接受可能带 ``;charset=...`` 后缀的 content-type header（先 strip 再判断）。
- :func:`is_text_media_type` — 检查非 JSON 的 media type 是否为文本型（用于
  :class:`stoma.RawResponseSpec` 的 ``.text(...)`` / ``.bytes(...)`` 工厂方法
  分派）。``text/*`` + 一组已知文本 subtype（``xml`` / ``javascript`` /
  ``yaml`` / ``xhtml+xml`` / ``csv`` / ``event-stream`` / ``atom+xml`` /
  ``rss+xml``）。
- :func:`sanitize_media_type` — 将 media type 字符串转换为合法 Python
  标识符片段（用于在 renderer 中作为多 media type 区分的属性名后缀）。
  先按 ``;`` 切分丢弃参数部分（仅清洗主类型），再链式替换 ``/``、``+``、
  ``-``、``.``、空格 为 ``_``，其中 ``+`` 替换为 ``_plus_`` 以保留语义
  可读性。例如 ``text/xml; charset=utf-8`` → ``text_xml``
  （而非 ``text_xml__charset_utf_8``）。
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


def is_text_media_type(media_type: str) -> bool:
    """检查 media type 是否为文本型。

    用于 :class:`stoma.RawResponseSpec` 工厂方法分派（``text(...)`` vs
    ``bytes(...)``）——``RawResponseSpec`` 必须显式指定 ``T`` 类型参数，
    因此 renderer 在生成 ``ClassVar[RawResponseSpec] = ...`` 时必须调用
    ``.text(...)`` / ``.bytes(...)`` 之一（裸 ``RawResponseSpec(...)`` 会在
    ``__init__`` 抛 ``TypeError``）。

    文本型（返回 ``True`` → ``.text(...)``）：

    - ``text/*`` 前缀（如 ``text/plain`` / ``text/html`` / ``text/xml`` /
      ``text/event-stream`` / ``text/csv``）。
    - 一组已知文本 subtype：
      ``application/xml`` / ``application/javascript`` /
      ``application/xhtml+xml`` / ``application/atom+xml`` /
      ``application/rss+xml`` / ``application/yaml`` /
      ``application/x-yaml`` / ``application/csv``。
    - ``application/*+xml`` / ``application/*+yaml`` structured syntax suffix
      （如 ``application/soap+xml``）。

    其他所有非 JSON media type（如 ``application/octet-stream`` /
    ``image/*`` / ``audio/*`` / ``video/*``）返回 ``False`` → ``.bytes(...)``。

    注意：本函数处理的是已被 :func:`is_json_media_type` 排除后的剩余
    media type；``application/json`` / ``application/*+json`` 已被分流到
    :class:`stoma.JSONResponseSpec`，不会传入本函数。

    支持 content-type header 直接传入：先 strip ``;charset=...`` 等参数，
    再做判断。空字符串返回 ``False``。

    :param media_type: media type 字符串，可能带 ``;charset=...`` 后缀。
    :return: 是文本型 media type 返回 ``True``，否则返回 ``False``。
    """
    if not media_type:
        return False
    # strip ;charset=... 等参数
    main = media_type.split(";", 1)[0].strip().lower()
    if main.startswith("text/"):
        return True
    text_subtypes = frozenset(
        {
            "application/xml",
            "application/javascript",
            "application/xhtml+xml",
            "application/atom+xml",
            "application/rss+xml",
            "application/yaml",
            "application/x-yaml",
            "application/csv",
        }
    )
    if main in text_subtypes:
        return True
    return main.endswith("+xml") or main.endswith("+yaml")


def sanitize_media_type(media_type: str) -> str:
    """将 media type 字符串清洗为合法 Python 标识符片段。

    先按 ``;`` 切分丢弃参数部分（仅清洗主类型，如 ``text/xml; charset=utf-8``
    只清洗 ``text/xml``），再链式执行以下替换（顺序固定，保证确定性输出）：
    1. ``lower()`` 归一化大小写。
    2. ``/`` → ``_``，分隔 type/subtype。
    3. ``+`` → ``_plus_``，保留 RFC 6839 structured syntax suffix 语义。
    4. ``-`` → ``_``，如 ``json-patch+json`` → ``json_patch_plus_json``。
    5. ``.`` → ``_``，如 ``vnd.api+json`` → ``vnd_api_plus_json``。
    6. 空格 → ``_``，处理 ``application/ld+json; charset=utf-8`` 这种
       主类型内含空格的形式。

    函数为纯字符串变换，无副作用，对相同输入总是返回相同结果。

    :param media_type: 原始 media type 字符串，可能带 ``;charset=...``
        后缀、混合大小写或含 ``+``、``-``、``.`` 等字符。
    :return: 可直接用作 Python 标识符的清洗后字符串。
    """
    main = media_type.split(";", 1)[0]  # discard after ;
    return main.lower().replace("/", "_").replace("+", "_plus_").replace("-", "_").replace(".", "_").replace(" ", "_")


__all__ = ["is_json_media_type", "is_text_media_type", "sanitize_media_type"]
