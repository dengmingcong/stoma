"""响应封装类型。

定义框架统一返回的响应包装类型。

``Response[T]`` 是 dataclass（而非 Pydantic BaseModel），因为 ``raw`` 字段
持有 Playwright 的 ``APIResponse`` 对象，该对象不是 Pydantic 可识别的类型。
使用 dataclass 既避免了 ``arbitrary_types_allowed`` 的额外配置，又保留了
简洁的类型注解能力。

设计要点：

- ``raw``：Playwright 原始响应对象，类型为 ``playwright.sync_api.APIResponse``，
  提供完整 HTTP 协议层访问（``status`` / ``headers`` / ``text()`` / ``body()`` / ``json()``）。
- ``model``：仅当响应 content-type 为 JSON（含 ``+json`` 后缀）时填充，
  用 Pydantic 验证后的 ``T`` 类型实例；其他 content-type 时为 ``None``。
"""

from dataclasses import dataclass

from playwright.sync_api import APIResponse


@dataclass
class Response[T]:
    """框架对外的统一响应封装。

    始终返回 ``Response[T]``，不论 HTTP 状态码是否为错误。
    调用方通过 ``raw.status`` 判断请求成功/失败。

    字段说明：

    - ``raw``：Playwright 原始响应对象，提供完整 HTTP 协议层访问。
    - ``model``：仅当响应 content-type 为 JSON（含 ``+json`` 后缀）时，
      用 Pydantic 验证后的 ``T`` 类型实例；其他 content-type 时为 ``None``，
      此时调用方应使用 ``raw.text()`` / ``raw.body()`` 获取原始数据。

    :var raw: Playwright 原始响应对象。
    :vartype raw: APIResponse
    :var model: JSON 响应解析后的 Pydantic 模型实例，其他 content-type 时为 None。
    :vartype model: T | None

    Example::

        response = endpoint.send(context)
        if response.raw.status == 200:
            user = response.model  # 类型为 UserData
        else:
            log.error(f"failed: {response.raw.status}")
    """

    raw: APIResponse
    model: T | None = None
