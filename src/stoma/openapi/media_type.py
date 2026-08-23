"""OpenAPI / HTTP media type 判定工具。"""

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


__all__ = ["is_json_media_type", "sanitize_media_type"]
