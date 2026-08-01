"""API Client，统一管理 Playwright context 和请求发送。

Client 是 stoma 的运行时入口，封装所有 HTTP 细节：
- 持有 Playwright APIRequestContext（用户提供）
- 从 APIRoute 提取参数（path、headers、body）
- 发送 HTTP 请求
- 解析响应并按 content-type 派发

调用模式：
    ctx = pw.request.new_context(base_url="http://localhost:8000")
    client = Client(context=ctx)
    response = client.send(GetUsers(limit=10))
    # response: Response[list[UserData]]，T 从 GetUsers 推断

URL/Query 处理说明：
- base_url 由 Playwright context 管理（new_context 时设置）
- 查询参数通过 Playwright 的 ``params=dict`` 参数自动拼接为 query string
- 路径参数（{user_id}）需要手动插值
- 路径只需相对路径（如 /users/123），Playwright 自动拼接 base_url
"""

from dataclasses import asdict, is_dataclass
from typing import Any, NamedTuple

from playwright.sync_api import APIRequestContext, APIResponse
from pydantic import BaseModel

from src.dependencies import Dependant
from src.dependencies.utils import field_annotation_is_complex
from src.exceptions import HTTPError, ParseError, ValidationError
from src.params import Body
from src.response import Response
from src.routing import APIRoute


class BodyItem(NamedTuple):
    """body 项。"""

    alias: str
    dumped: dict[str, Any] | Any


class Client:
    """API Client，统一管理 Playwright context。

    :param context: Playwright APIRequestContext 实例（由用户创建）。
    :type context: APIRequestContext

    Example::

        ctx = pw.request.new_context(
            base_url="http://localhost:8000",
            extra_http_headers={"Authorization": "Bearer xxx"},
        )
        client = Client(context=ctx)

        endpoint = GetUsers(limit=10)
        response = client.send(endpoint)
        # IDE: response 类型为 Response[list[UserData]]，T 从 GetUsers 推断
        # response.data: list[UserData] | None
        # response.raw: Playwright APIResponse
    """

    def __init__(self, context: APIRequestContext) -> None:
        """初始化 Client。

        :param context: Playwright APIRequestContext 实例。
        :type context: APIRequestContext
        """
        self._context = context

    def send[T](self, api_route: APIRoute[T]) -> Response[T]:
        """发送 api_route 请求，返回 Response[T]。

        T 通过 PEP 695 泛型方法从 api_route 的类型参数自动推断。

        :param api_route: APIRoute 实例。
        :type api_route: APIRoute[T]
        :return: 包装后的响应，类型为 Response[T]。
        :rtype: Response[T]
        :raise HTTPError: 仅在网络层失败时抛出。
        :raise ParseError: 当 content-type 为 JSON 但响应体无法解析。
        :raise ValidationError: 当 JSON 解析成功但不符合 T。
        """
        try:
            method, path, params, headers, data = self._extract_request_params(api_route)
            api_response = self._execute_request(method, path, params, headers, data)
            return self._build_response(api_route, api_response)
        except (HTTPError, ParseError, ValidationError):
            raise
        except Exception as e:
            msg = f"请求发送失败: {e}"
            raise HTTPError(msg) from e

    def dispose(self) -> None:
        """释放 Playwright context。"""
        self._context.dispose()

    # ===== 私有方法：从 APIRoute 提取请求参数 =====

    def _extract_request_params(
        self,
        api_route: APIRoute,
    ) -> tuple[str, str, dict[str, Any], dict[str, str], dict[str, Any] | None]:
        """从 api_route 提取（method, path, params, headers, body）。

        path 是相对路径，Playwright 会自动拼接 base_url。
        params 是 dict，Playwright 自动拼接为 query string。
        body 是 dict，Playwright 会自动序列化为 JSON 并设置 Content-Type: application/json。
        """
        dependant = api_route._get_dependant()
        path = self._interpolate_path_params(api_route, dependant)
        params = self._collect_query_params(api_route, dependant)
        headers = self._serialize_header_params(api_route, dependant)
        body = self._serialize_body_params(api_route, dependant)
        return dependant.method, path, params, headers, body

    def _interpolate_path_params(
        self,
        api_route: APIRoute,
        dependant: Dependant,
    ) -> str:
        """插值路径参数（将 {param} 占位符替换为实际值）。

        :return: 插值后的相对路径字符串。
        """
        path = dependant.path
        for model_field in dependant.path_params:
            value = getattr(api_route, model_field.name)
            placeholder = f"{{{model_field.name}}}"
            path = path.replace(placeholder, str(value))
        return path

    def _collect_query_params(
        self,
        api_route: APIRoute,
        dependant: Dependant,
    ) -> dict[str, Any]:
        """收集查询参数为 dict（Playwright 自动拼接为 query string）。

        规则：
        - None 值：跳过
        - 其他类型：直接传递，Playwright 自动转换
        """
        query: dict[str, Any] = {}
        for model_field in dependant.query_params:
            value = getattr(api_route, model_field.name)
            if value is None:
                continue
            query[model_field.alias] = value
        return query

    def _serialize_header_params(
        self,
        api_route: APIRoute,
        dependant: Dependant,
    ) -> dict[str, str]:
        """序列化请求头参数为 dict。

        规则：
        - None 值：跳过
        - 布尔值：转换为 'true'/'false'（HTTP 约定）
        - 其他类型：str() 转换（HTTP header 值必须是字符串）
        - 别名：使用 Annotated[Type, Header(alias="...")] 显式设置；否则 snake_case → kebab-case
        """
        headers: dict[str, str] = {}
        for model_field in dependant.header_params:
            value = getattr(api_route, model_field.name)
            if value is None:
                continue
            if isinstance(value, bool):
                value = "true" if value else "false"
            else:
                value = str(value)

            alias = model_field.alias
            if alias == model_field.name:
                alias = alias.replace("_", "-")
            headers[alias] = value
        return headers

    def _serialize_body_params(
        self,
        api_route: APIRoute,
        dependant: Dependant,
    ) -> dict[str, Any] | None:
        """根据 FastAPI Body Multiple Parameters 规则序列化请求体为 JSON 字符串。

        规则（参考 https://fastapi.tiangolo.com/tutorial/body-multiple-params/）：

        - 单个 Pydantic 模型（自动识别）：平展
        - 多个 body 参数：每个独立嵌入
        - Body(embed=True)：嵌入
        - 标量 Body()：嵌入
        """
        if not dependant.body_params:
            return None

        has_multiple = len(dependant.body_params) > 1
        body_items: list[BodyItem] = []

        # 循环中只做序列化，不做判断
        for model_field in dependant.body_params:
            value = getattr(api_route, model_field.name)
            if value is None:
                continue

            # 序列化
            if isinstance(value, BaseModel):
                dumped = value.model_dump(exclude_none=True)
            elif is_dataclass(value) and not isinstance(value, type):
                dumped = asdict(value)
            elif hasattr(value, "model_dump"):
                dumped = value.model_dump(exclude_none=True)
            else:
                dumped = value

            body_items.append(BodyItem(model_field.alias, dumped))

        # 统一处理
        if not body_items:
            return None

        # 多个 body 参数：必须嵌入
        if has_multiple:
            return {item.alias: item.dumped for item in body_items}

        # 单个 body 参数：根据 Body(embed=...) 或是否为标量类型决定是否嵌入
        model_field = dependant.body_params[0]
        param_info = model_field.param_info
        is_explicit_body = isinstance(param_info, Body)
        explicit_embed = getattr(param_info, "embed", False) if is_explicit_body else False
        field_type = model_field.field_info.annotation

        should_embed = (
            (is_explicit_body and explicit_embed)
            or (is_explicit_body and not field_annotation_is_complex(field_type))
        )

        if not should_embed:
            return body_items[0].dumped

        return {body_items[0].alias: body_items[0].dumped}

    # ===== 私有方法：发送请求 =====

    def _execute_request(
        self,
        method: str,
        path: str,
        params: dict[str, Any],
        headers: dict[str, str],
        data: dict[str, Any] | None,
    ) -> APIResponse:
        """用 self._context 发送 HTTP 请求。

        Playwright 自动处理：
        - base_url 拼接（在 context 创建时设置）
        - query string 拼接（通过 params 参数）
        - body 序列化为 JSON 并设置 Content-Type: application/json（通过 data=dict）

        :param method: HTTP 方法。
        :param path: 相对路径。
        :param params: 查询参数 dict。
        :param headers: 请求头 dict。
        :param data: body dict（Playwright 自动序列化为 JSON）。
        :return: Playwright APIResponse 对象。
        :raise HTTPError: 网络层失败。
        """
        method_map = {
            "GET": self._context.get,
            "POST": self._context.post,
            "PUT": self._context.put,
            "PATCH": self._context.patch,
            "DELETE": self._context.delete,
        }
        request_method = method_map.get(method)
        if request_method is None:
            msg = f"不支持的 HTTP 方法: {method}"
            raise HTTPError(msg)

        try:
            return request_method(
                path,
                params=params if params else None,
                headers=headers if headers else None,
                data=data,
            )
        except Exception as e:
            msg = f"HTTP 请求失败: {e}"
            raise HTTPError(msg) from e

    # ===== 私有方法：构造响应 =====

    def _build_response[T](
        self,
        api_route: APIRoute[T],
        api_response: APIResponse,
    ) -> Response[T]:
        """从 Playwright APIResponse 构造 Response[T]。

        流程：
        1. 直接持有 Playwright 原始响应对象作为 raw
        2. 解析 content-type 派发：JSON 路径用 T 验证，其他保持 None
        3. 4xx/5xx 不抛错，由 raw.status 判断

        :param api_route: APIRoute 实例（提供 T）。
        :param api_response: Playwright 响应对象。
        :return: 包装后的 Response[T]。
        :raise ParseError: JSON 解析失败。
        :raise ValidationError: JSON 验证失败。
        """
        dependant = api_route._get_dependant()

        # 1. 解析 content-type
        content_type = api_response.headers.get("content-type", "") if api_response.headers else ""
        media_type = content_type.split(";")[0].strip().lower()

        # 2. 特殊：204 No Content → model = None
        if api_response.status == 204:
            return Response[T](raw=api_response, data=None)

        # 3. 仅当 content-type 为 JSON 时才解析并填充 model
        if media_type.startswith("application/json") or media_type.endswith("+json"):
            try:
                payload: Any = api_response.json()
            except Exception as e:
                fallback_text = ""
                try:
                    fallback_text = api_response.text() if hasattr(api_response, "text") else ""
                except Exception:
                    pass
                msg = f"响应 JSON 解析失败: {e}"
                raise ParseError(msg, response_text=fallback_text) from e

            if dependant.response_type is type(None):
                return Response[T](raw=api_response, data=None)

            assert dependant.response_type_adapter is not None
            try:
                validated = dependant.response_type_adapter.validate_python(payload)  # type: ignore[no-any-return]
            except Exception as e:
                msg = f"响应数据验证失败: {e}"
                errors: list[dict[str, Any]] = []
                if hasattr(e, "errors"):
                    errors = list(e.errors())
                raise ValidationError(msg, errors=errors) from e

            return Response[T](raw=api_response, data=validated)

        # 4. 非 JSON 响应：model = None
        return Response[T](raw=api_response, data=None)
