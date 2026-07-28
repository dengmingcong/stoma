"""响应封装类型。

定义框架统一返回的响应包装类型，包括：

- RawResponse：HTTP 层原始响应信息。
- Response：框架对外返回的响应封装，包含原始响应与业务数据。
"""

from pydantic import BaseModel, ConfigDict


class RawResponse(BaseModel):
    """HTTP 层原始响应。

    镜像 Lark SDK 的 RawResponse 设计，
    仅承载与 HTTP 协议相关的原始信息（不解析业务字段）。

    :var status_code: HTTP 状态码。
    :vartype status_code: int
    :var headers: HTTP 响应头（保持服务端原始大小写，框架不强制规范化）。
    :vartype headers: dict[str, str]
    :var content: 原始响应字节。
    :vartype content: bytes
    """

    model_config = ConfigDict(frozen=True)

    status_code: int
    headers: dict[str, str]
    content: bytes


class Response[T](BaseModel):
    """框架对外的统一响应封装。

    始终返回 ``Response[T]``，不论 HTTP 状态码是否为错误。
    调用方通过 ``raw.status_code`` 判断请求成功/失败。

    字段说明：

    - ``raw``：HTTP 层原始信息（状态码、响应头、字节内容）。
    - ``model``：仅当响应 content-type 为 JSON（含 ``+json`` 后缀）时，
      用 Pydantic 验证后的 ``T`` 类型实例；其他 content-type 时为 ``None``，
      此时调用方应使用 ``raw.content`` 获取原始字节。

    :var raw: HTTP 层原始响应。
    :vartype raw: RawResponse
    :var model: JSON 响应解析后的 Pydantic 模型实例，其他 content-type 时为 None。
    :vartype model: T | None

    Example::

        response = endpoint.send(context)
        if response.raw.status_code == 200:
            user = response.model  # 类型为 UserData
        else:
            log.error(f"failed: {response.raw.status_code}")
    """

    raw: RawResponse
    model: T | None = None
