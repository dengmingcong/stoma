"""OpenAPI status code 派发与渲染工具。

包含两个工具函数：

- :func:`render_status_code_kwarg` —— 将 :class:`int` 或 lambda 源字符串转为模板可嵌入的字面量。
- :func:`parse_status_key` —— 将 OpenAPI responses dict 的 status key（精确 int /
  ``default`` / ``4XX`` 等）转为 ``(attr_base, status_code)`` 元组，供
  :class:`stoma.openapi.renderer.EndpointRenderer` 派发使用。
"""

from __future__ import annotations

__all__ = ["parse_status_key", "render_status_code_kwarg"]


def render_status_code_kwarg(status_code: int | str) -> str:
    """将 ``status_code`` 渲染为构造调用的关键字参数片段。

    输出已含参数名 ``status_code=`` 前缀，模板直接嵌入。两种形态：

    - 精确匹配 ``int``（如 ``200``）→ ``"status_code=200"``。
    - lambda 源字符串（以 ``"lambda c: "`` 起头，如
      ``"lambda c: c not in [200]"`` / ``"lambda c: 400 <= c < 500"``）→
      ``"status_code=lambda c: c not in [200]"``。

    在 :class:`stoma.BaseResponseSpec` v2 重构后，``status_code`` 参数既可
    接 ``int`` 也可直接接 ``Callable``，``callable=`` 别名已被移除，
    因此 lambda 走 ``status_code=lambda ...`` 关键字也合法——模板统一用
    ``status_code=`` 一条关键字处理两种情形。

    :param status_code: 精确匹配为 ``int``；通配符为 lambda 源字符串
        （``"lambda c: <predicate>"``）。
    :return: 可直接嵌入模板的代码片段字符串。
    :raise ValueError: ``status_code`` 既非 ``int``、也非以 ``"lambda c: "`` 起头的源字符串。
    """
    if isinstance(status_code, int):
        return f"status_code={status_code}"
    if isinstance(status_code, str) and status_code.startswith("lambda c: "):
        return f"status_code={status_code}"
    msg = f"Cannot render status_code {status_code!r} to code-generation kwarg"
    raise ValueError(msg)


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
