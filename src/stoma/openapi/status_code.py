"""OpenAPI status code 派发工具。

包含 :func:`parse_status_key` —— 将 OpenAPI responses dict 的 status key（精确 int /
``default`` / ``4XX`` 等）转为 ``(attr_base, status_code)`` 元组，供
:class:`stoma.openapi.renderer.EndpointRenderer` 派发使用。
"""

from __future__ import annotations

__all__ = ["parse_status_key"]


def parse_status_key(
    status_key: str,
    other_int_codes: list[int],
) -> tuple[str, int | str]:
    """解析 OpenAPI 状态码 key 为 ``(attr_base, status_code)``。

    ``status_code`` 字段携带的语义：

    - 精确匹配为 ``int``——模板中以 ``status_code=200`` 形式嵌入；
    - 通配符为 lambda 源字符串（``"lambda c: c not in [200]"`` /
      ``"lambda c: 400 <= c < 500"``）——模板中以
      ``status_code=lambda c: c not in [200]`` 形式嵌入。

    三类形态：

    - ``"default"`` → ``attr_base="on_default"``，
      ``status_code="lambda c: c not in [<other_int_codes>]"``。
      ``other_int_codes`` 是同一 endpoint 中已声明的所有 int 状态码（不含
      任何 wildcard），按升序排序——``default`` 反向谓词负责排除这些 code，
      与 OpenAPI「未列出的 status 走 default」语义一致。当无其他 int code
      时生成 ``lambda c: c not in []``，语义等价于 ``lambda c: True``。
    - 通配符 ``"1XX"`` / ``"NXX"``（大小写不敏感）→ ``attr_base="on_4xx"``
      等（小写），``status_code=f"lambda c: {start} <= c < {end}"``
      （半开区间，含 ``start``、不含 ``end``）。
    - 3 位数字（``"200"`` / ``"404"`` 等）→ ``attr_base="on_200"``、
      ``status_code=200``（``int``）。

    :param status_key: OpenAPI responses 字典的 key 字符串。
    :param other_int_codes: 同一 endpoint 中已声明的所有 int 状态码列表，
        仅在 ``status_key == "default"`` 时使用——``default`` lambda 排除
        这些 code。
    :return: 二元组 ``(attr_base, status_code)``。
    """
    if status_key == "default":
        excluded = sorted(other_int_codes)
        excluded_str = ", ".join(str(c) for c in excluded)
        return "on_default", f"lambda c: c not in [{excluded_str}]"
    upper = status_key.upper()
    if len(upper) == 3 and upper[1:] == "XX" and upper[0] in "12345":
        digit = int(upper[0])
        return f"on_{digit}xx", f"lambda c: {digit * 100} <= c < {digit * 100 + 100}"
    code = int(status_key)
    return f"on_{code}", code
