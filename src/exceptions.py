"""框架自定义异常类。

此模块定义了框架在接口调用过程中可能抛出的各类异常，
便于用户进行精确的错误处理和测试断言。
"""

from typing import Any


class StomaError(Exception):
    """Stoma 框架的基础异常类。

    所有框架自定义异常都应继承自此类。
    """

    pass


class ValidationError(StomaError):
    """参数验证失败异常。

    当请求参数不符合 Pydantic 模型定义的验证规则，
    或响应数据无法通过 Pydantic 模型验证时抛出。

    :var message: 错误消息。
    :vartype message: str
    :var errors: Pydantic 验证错误详情列表（可选）。
    :vartype errors: list[dict[str, Any]] | None

    Example::

        try:
            endpoint = GetUsers(limit=-1)  # 参数验证失败
        except ValidationError as e:
            print(e.message)
            print(e.errors)  # Pydantic 错误详情
    """

    def __init__(self, message: str, errors: list[dict[str, Any]] | None = None) -> None:
        """初始化验证错误。

        :param message: 错误消息。
        :type message: str
        :param errors: Pydantic 验证错误详情列表。
        :type errors: list[dict[str, Any]] | None
        """
        super().__init__(message)
        self.message = message
        self.errors = errors


class HTTPError(StomaError):
    """HTTP 请求失败异常。

    当 HTTP 请求发送失败、超时、或服务器返回错误状态码时抛出。

    :var message: 错误消息。
    :vartype message: str
    :var status_code: HTTP 状态码（如果有）。
    :vartype status_code: int | None
    :var response_text: 响应文本内容（如果有）。
    :vartype response_text: str | None

    Example::

        try:
            result = endpoint()
        except HTTPError as e:
            print(f"HTTP 请求失败: {e.message}")
            print(f"状态码: {e.status_code}")
            print(f"响应: {e.response_text}")
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_text: str | None = None,
    ) -> None:
        """初始化 HTTP 错误。

        :param message: 错误消息。
        :type message: str
        :param status_code: HTTP 状态码。
        :type status_code: int | None
        :param response_text: 响应文本内容。
        :type response_text: str | None
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_text = response_text


class ParseError(StomaError):
    """响应解析失败异常。

    当服务器响应无法解析为 JSON，或 JSON 结构与预期不符时抛出。

    :var message: 错误消息。
    :vartype message: str
    :var response_text: 原始响应文本。
    :vartype response_text: str | None

    Example::

        try:
            result = endpoint()
        except ParseError as e:
            print(f"响应解析失败: {e.message}")
            print(f"原始响应: {e.response_text}")
    """

    def __init__(self, message: str, response_text: str | None = None) -> None:
        """初始化解析错误。

        :param message: 错误消息。
        :type message: str
        :param response_text: 原始响应文本。
        :type response_text: str | None
        """
        super().__init__(message)
        self.message = message
        self.response_text = response_text
