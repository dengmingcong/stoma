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
    # response: Response[T]，T 从 GetUsers 推断

URL/Query 处理说明：
- base_url 由 Playwright context 管理（new_context 时设置）
- 查询参数通过 Playwright 的 ``params=dict`` 参数自动拼接为 query string
- 路径参数（{user_id}）需要手动插值
- 路径只需相对路径（如 /users/123），Playwright 自动拼接 base_url
"""

import json
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, NamedTuple

from playwright.sync_api import APIRequestContext, APIResponse, FormData
from pydantic import BaseModel

from src.dependencies import Dependant, ModelField
from src.dependencies.utils import field_annotation_is_complex
from src.exceptions import HTTPError, ParseError, ValidationError
from src.params import Body, UploadFile
from src.response import Response
from src.routing import APIRoute


class BodyItem(NamedTuple):
    """body 项。"""

    alias: str
    dumped: dict[str, Any] | Any


class RequestBodyKind(Enum):
    """请求体类型枚举。"""

    JSON = "application/json"
    URLENCODED = "application/x-www-form-urlencoded"
    MULTIPART = "multipart/form-data"


@dataclass
class RequestBody:
    """请求体数据结构。

    用于在序列化过程中携带不同类型请求体的元信息。

    :var kind: 请求体类型。
    :var json_body: JSON 请求体数据（当 kind 为 JSON 时）。
    :var form_data: 表单请求体数据（当 kind 为 URLENCODED 或 MULTIPART 时）。
    """

    kind: RequestBodyKind
    json_body: dict | None = None
    form_data: FormData | None = None


class RequestParams(NamedTuple):
    """请求参数元组。

    从 ``_extract_request_params`` 返回，替代原有的 tuple[str, str, dict[str, Any], dict[str, str], RequestBody]，
    提供命名字段以提升可读性。

    :var method: HTTP 方法。
    :var path: 相对路径。
    :var params: 查询参数字典。
    :var headers: 请求头字典。
    :var body: 请求体数据结构。
    """

    method: str
    path: str
    params: dict[str, Any]
    headers: dict[str, str]
    body: RequestBody


def _is_scalar_type(value: Any) -> bool:
    """判断 ``value`` 是否为 Form 标量（``str`` / ``int`` / ``float`` / ``bool`` / ``bytes``）。"""
    return isinstance(value, (str, int, float, bool, bytes))


def _fill_scalar_form_field(form_data: FormData, model_field: ModelField, value: Any) -> None:
    """填充函数级 Form 字段到 FormData。

    按 ``model_field.param_info.kind`` 派发（由 ``src.routing`` 在分类阶段写入）：

    - ``"scalar"``：``form_data.set(alias, value)``，原值传递，不做 JSON 序列化。
    - ``"list"``：逐个元素 ``form_data.append(alias, elem)``，同名多 part。

    ``None`` 值（字段本身或 list 元素）一律跳过；空 list 相当于整个字段不出现。

    :param form_data: 待填充的表单。
    :param model_field: Form 字段定义。
    :param value: 字段值。
    :raise ValueError: 当值类型与注解不匹配，或值为 ``bytes`` / ``dict``
        等 stoma 不再自动序列化的类型。
    """
    if value is None:
        return

    if model_field.param_info.kind == "list":  # type: ignore[union-attr]
        if not isinstance(value, list):
            msg = f"Form 字段 {model_field.alias!r} 注解为 list，但收到 {type(value).__name__}"
            raise ValueError(msg)
        for element in value:
            if element is None:
                continue
            _append_list_form_element(form_data, model_field.alias, element)
        return

    _set_scalar_form_value(form_data, model_field.alias, value)


def _set_scalar_form_value(form_data: FormData, alias: str, value: Any) -> None:
    """将单个标量值写入 FormData。

    :param form_data: 待填充的表单。
    :param alias: 表单字段名。
    :param value: 字段值（非 None）。
    :raise ValueError: 当值不是 Playwright 支持的标量类型。
    """
    # bytes 也满足 ``_is_scalar_type``，必须先于标量分支拦截。
    if isinstance(value, bytes):
        msg = (
            f"Form 字段 {alias!r} 收到 bytes 类型。"
            f"stoma 不支持直接序列化 bytes（Playwright FormDataValue 不含 bytes）；"
            f"请自行 json.dumps 为 str 后传入。"
        )
        raise ValueError(msg)

    if _is_scalar_type(value):
        form_data.set(alias, value)
        return

    if isinstance(value, BaseModel):
        msg = (
            f"Form 字段 {alias!r} 收到 BaseModel 实例。"
            f"stoma 不支持嵌套 BaseModel Form；"
            f"请使用单独的 Form 字段，或将 BaseModel 内容平铺。"
        )
        raise ValueError(msg)

    msg = (
        f"Form 字段 {alias!r} 收到 {type(value).__name__}。"
        f"stoma 不再自动 JSON 序列化 form 字段；"
        f"若要传递 list/dict 等复合类型，请自行 json.dumps 为 str 后传入。"
    )
    raise ValueError(msg)


def _append_list_form_element(form_data: FormData, alias: str, element: Any) -> None:
    """将 list 字段的单个元素追加到 FormData。

    :param form_data: 待填充的表单。
    :param alias: 表单字段名。
    :param element: list 元素（非 None）。
    :raise ValueError: 当元素类型与注解不匹配。
    """
    # bytes 也满足 ``_is_scalar_type``，必须先于标量分支拦截。
    if isinstance(element, bytes):
        msg = (
            f"Form 字段 {alias!r} 元素收到 bytes 类型。"
            f"stoma 不支持直接序列化 bytes（Playwright FormDataValue 不含 bytes）；"
            f"请自行 json.dumps 为 str 后传入。"
        )
        raise ValueError(msg)

    if not _is_scalar_type(element):
        msg = (
            f"Form 字段 {alias!r} 元素收到 {type(element).__name__}。"
            f"stoma 不再自动 JSON 序列化 form 字段元素；"
            f"请自行 json.dumps 为 str 后传入。"
        )
        raise ValueError(msg)

    form_data.append(alias, element)


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
        # response.validated: list[UserData] | None
        # response.raw: Playwright APIResponse
    """

    def __init__(self, context: APIRequestContext) -> None:
        """初始化 Client。

        :param context: Playwright APIRequestContext 实例。
        :type context: APIRequestContext
        """
        self._context = context

    def send[T](
        self,
        api_route: APIRoute[T],
    ) -> Response[T]:
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
            result = self._extract_request_params(api_route)
            api_response = self._execute_request(
                result.method, result.path, result.params, result.headers, result.body
            )
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
    ) -> RequestParams:
        """从 api_route 提取请求参数。

        返回 ``RequestParams`` 命名元组，包含 method、path、params、headers、body。

        :return: 命名元组，包含提取后的请求参数。
        :rtype: RequestParams
        """
        dependant = api_route._get_dependant()
        path = self._interpolate_path_params(api_route, dependant)
        params = self._collect_query_params(api_route, dependant)
        headers = self._serialize_header_params(api_route, dependant)
        body = self._serialize_body_params(api_route, dependant)
        return RequestParams(
            method=dependant.method,
            path=path,
            params=params,
            headers=headers,
            body=body,
        )

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
            placeholder = f"{{{model_field.alias}}}"
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

            headers[model_field.alias] = value
        return headers

    def _serialize_body_params(
        self,
        api_route: APIRoute,
        dependant: Dependant,
    ) -> RequestBody:
        """按请求体字段列表分派，序列化为 RequestBody。

        Form 仅接受标量或 ``list[标量]`` 注解（含 Optional 形式）。
        ``form_body_params`` 字段由 ``_fill_scalar_form_field`` 填充：list 值通过
        ``form_data.append`` 派发同名多 part。

        函数级 ``UploadFile`` 或 ``list[UploadFile]`` 由 routing 路由到
        ``file_body_params``，与 multipart 容器共用 ``FormData``。

        分派规则：

        - 存在文件字段（``file_body_params``）：multipart/form-data。
        - 仅有表单字段（``form_body_params``）：application/x-www-form-urlencoded。
        - 其余情况：application/json，沿用 FastAPI Body Multiple Parameters 规则。

        :param api_route: APIRoute 实例。
        :param dependant: 参数依赖定义。
        :return: 序列化后的请求体。
        :raise ValueError: 当遇到 Form 不支持的字段类型时（如 ``bytes``）。
        """
        has_files = bool(dependant.file_body_params)
        form_data = FormData()

        for model_field in dependant.form_body_params:
            value = getattr(api_route, model_field.name)
            if value is None:
                continue
            _fill_scalar_form_field(form_data, model_field, value)

        for model_field in dependant.file_body_params:
            value = getattr(api_route, model_field.name)
            if value is None:
                continue
            # 注意：annotation 可能是 ``UploadFile | None`` / ``list[UploadFile] | None``，
            # ``field_info.annotation is UploadFile`` / ``get_origin(...) is list`` 会失效。
            # 这里改为按运行时值类型分发，对必填 / 可选（空列表视为跳过）都成立。
            if isinstance(value, UploadFile):
                form_data.set(model_field.alias, value.path)
            elif isinstance(value, list):
                # FormData.append 支持同一 key 多次出现，多次 part 对应多次同名字段。
                for upload_file in value:
                    form_data.append(model_field.alias, upload_file.path)

        if has_files:
            return RequestBody(kind=RequestBodyKind.MULTIPART, form_data=form_data)
        # FormData 没有 ``__bool__`` / ``__len__``，空实例仍为真，必须用 ``_fields`` 判断非空。
        if form_data._fields:
            return RequestBody(kind=RequestBodyKind.URLENCODED, form_data=form_data)
        return RequestBody(kind=RequestBodyKind.JSON, json_body=self._build_json_body(api_route, dependant))

    def _build_json_body(
        self,
        api_route: APIRoute,
        dependant: Dependant,
    ) -> dict[str, Any]:
        """根据 FastAPI Body Multiple Parameters 规则序列化 JSON 请求体。

        规则（参考 https://fastapi.tiangolo.com/tutorial/body-multiple-params/）：

        - 单个 Pydantic 模型（自动识别）：平展
        - 多个 body 参数：每个独立嵌入
        - Body(embed=True)：嵌入
        - 标量 Body()：嵌入

        :param api_route: APIRoute 实例。
        :param dependant: 参数依赖定义。
        :return: JSON 请求体，无请求体字段时返回空字典。
        """
        if not dependant.pure_body_params:
            return {}

        has_multiple = len(dependant.pure_body_params) > 1
        body_items: list[BodyItem] = []

        # 循环中只做序列化，不做判断
        for model_field in dependant.pure_body_params:
            value = getattr(api_route, model_field.name)
            if value is None:
                continue

            # 序列化
            if isinstance(value, BaseModel):
                dumped = value.model_dump(by_alias=True, exclude_none=True)
            elif is_dataclass(value) and not isinstance(value, type):
                dumped = asdict(value)
            else:
                dumped = value

            body_items.append(BodyItem(model_field.alias, dumped))

        # 统一处理
        if not body_items:
            return {}

        # 多个 body 参数：必须嵌入
        if has_multiple:
            return {item.alias: item.dumped for item in body_items}

        # 单个 body 参数：根据 Body(embed=...) 或是否为标量类型决定是否嵌入
        model_field = dependant.pure_body_params[0]
        param_info = model_field.param_info
        is_explicit_body = isinstance(param_info, Body)
        # 仅 Body 类有效；Form 已移除 embed（T1 变更）。
        explicit_embed = getattr(param_info, "embed", False) if is_explicit_body else False
        field_type = model_field.field_info.annotation

        should_embed = (is_explicit_body and explicit_embed) or (
            is_explicit_body and not field_annotation_is_complex(field_type)
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
        body: RequestBody,
    ) -> APIResponse:
        """用 self._context 发送 HTTP 请求。

        统一通过 Playwright ``fetch`` 入口发送任意 HTTP 方法请求。
        Playwright 自动处理：
        - base_url 拼接（在 context 创建时设置）
        - query string 拼接（通过 params 参数）
        - 请求体编码（JSON 用 data，urlencoded 用 form，multipart 用 multipart）

        :param method: HTTP 方法（支持 GET/POST/PUT/PATCH/DELETE/HEAD/OPTIONS/TRACE 等）。
        :param path: 相对路径。
        :param params: 查询参数 dict。
        :param headers: 请求头 dict。
        :param body: 序列化后的请求体。
        :return: Playwright APIResponse 对象。
        :raise HTTPError: 网络层失败时抛出，消息包含 method/path 便于排错。
        """
        payload: dict[str, Any] = {"data": body.json_body if body.json_body else None}
        if body.kind is RequestBodyKind.MULTIPART:
            payload = {"multipart": body.form_data}
        elif body.kind is RequestBodyKind.URLENCODED:
            payload = {"form": body.form_data}

        try:
            return self._context.fetch(
                path,
                method=method,
                params=params if params else None,
                headers=headers if headers else None,
                **payload,
            )
        except Exception as e:
            msg = f"HTTP 请求失败 ({method} {path}): {e}"
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

        # 2. 特殊：204 No Content → validated = None
        if api_response.status == 204:
            return Response[T](raw=api_response, validated=None)

        # 3. 仅当 content-type 为 JSON 时才解析并填充 validated
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

            if dependant.json_response_schema is None:
                return Response[T](raw=api_response, validated=None)

            assert dependant.json_response_schema_adapter is not None
            try:
                validated = dependant.json_response_schema_adapter.validate_python(payload)  # type: ignore[no-any-return]
            except Exception as e:
                msg = f"响应数据验证失败: {e}"
                errors: list[dict[str, Any]] = []
                # Pydantic 的 ValidationError 才有 .errors() 方法
                if hasattr(e, "errors"):
                    errors = list(e.errors())  # type: ignore[no-any-return]
                raise ValidationError(msg, errors=errors) from e

            return Response[T](raw=api_response, validated=validated)

        # 4. 非 JSON 响应：validated = None
        return Response[T](raw=api_response, validated=None)
