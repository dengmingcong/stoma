"""Endpoint 路由文件渲染器。

把 OpenAPI 端点（:class:`src.openapi.models.Endpoint`）渲染成 ``route.py``
文件。**模型类由 ``datamodel-code-generator`` 在前置阶段生成**，本模块
只负责：

- 解析路径 / 查询 / 头部参数并渲染为 Pydantic 字段声明
- 解析请求体引用哪个模型（名字符串）
- 解析响应引用哪个模型（名字符串）
- 输出 ``from .models import ...`` 导入
"""

from __future__ import annotations

import shutil
import subprocess
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Literal, NamedTuple, Protocol

from jinja2 import Environment, FileSystemLoader, Template
from pydantic import BaseModel
from pydantic.alias_generators import to_snake

from stoma.exceptions import OpenAPISchemaError
from stoma.openapi.fields import (
    build_endpoint_docstring,
    build_form_field_line,
    build_scalar_body_line,
    build_upload_file_field_line,
    resolve_array_type,
)
from stoma.openapi.media_type import is_json_media_type, sanitize_media_type
from stoma.openapi.models import (
    BinaryRequestBodyFields,
    Endpoint,
    FieldDecl,
    JSONRequestBodyFields,
    MultipartFormRequestBodyFields,
    RequestBodyFields,
    ScalarRequestBodyFields,
    UrlencodedFormRequestBodyFields,
)
from stoma.openapi.naming import is_snake_case, to_pascal_case
from stoma.openapi.parameters import build_content_type_header, make_param_fields
from stoma.openapi.request_body import (
    flatten_body_fields,
    get_media_type_schema,
    is_body_fields_use_field,
)
from stoma.openapi.schema import (
    has_combinator,
    is_binary_schema_dict,
    is_primitive_schema_dict,
)
from stoma.openapi.type_mapping import is_primitive_json_type, python_type_name
from stoma.openapi.version import Reference30, Reference31, SpecVersion


class _ReferenceLike(Protocol):
    """Reference 类型的结构化形状（``Reference30`` / ``Reference31`` 都满足）。

    两者都是 :class:`pydantic.BaseModel` 的子类，并带一个别名到 ``$ref``
    的 ``ref: str`` 字段。用于 :class:`EndpointRenderer` 类型参数
    ``ReferenceT`` 的约束——纯 ``BaseModel`` 上界无法让 mypy 看到 ``ref``
    字段，因此用 Protocol 表达结构化约束；构造时传入的
    ``Reference: type[ReferenceT]`` 在运行时仍是 ``Reference30`` 或
    ``Reference31``，所以 ``isinstance`` 检测照常工作。
    """

    ref: str


class GenerationErrorKind(str, Enum):  # noqa: UP042
    """Codegen 错误的分类。

    :var MULTI_MEDIA_TYPE: endpoint 有多个 media type，已静默使用第一个。
    :vartype MULTI_MEDIA_TYPE: str
    :var MISSING_RESPONSE_MODEL: endpoint 引用的 Response 模型未在 ``models.py`` 中找到，已 fallback 到 generic。
    :vartype MISSING_RESPONSE_MODEL: str
    :var SCHEMA_UNSUPPORTED: spec 形态不被 stoma 当前实现支持，已跳过该 endpoint。
    :vartype SCHEMA_UNSUPPORTED: str
    :var DUPLICATE_RESPONSE_SPEC: 同一 ``(status, media_type)`` 在 responses 中重复出现，已跳过重复项。
    :vartype DUPLICATE_RESPONSE_SPEC: str
    """

    MULTI_MEDIA_TYPE = "multi_media_type"
    MISSING_RESPONSE_MODEL = "missing_response_model"
    SCHEMA_UNSUPPORTED = "schema_unsupported"
    DUPLICATE_RESPONSE_SPEC = "duplicate_response_spec"


@dataclass(frozen=True)
class GenerationError:
    """单条 codegen 错误记录。

    :var method: HTTP 方法（GET / POST / ...）。
    :vartype method: str
    :var path: 路径模板（如 ``/books/{book_id}``）。
    :vartype path: str
    :var kind: 错误分类。
    :vartype kind: GenerationErrorKind
    :var message: 人类可读的错误消息。
    :vartype message: str
    """

    method: str
    path: str
    kind: GenerationErrorKind
    message: str

    @property
    def location(self) -> str:
        """定位字符串，``"<METHOD> <PATH>"`` 形式。"""
        return f"{self.method} {self.path}"


class ResponseSpecDecl(NamedTuple):
    """单条响应声明（按 ``status_code + media_type`` 唯一）的渲染产物。

    由 :meth:`EndpointRenderer._extract_response_specs` 生成，
    供模板按 ``on_<attr_name>: ClassVar = ...`` 形式输出。
    ``is_json=True`` 对应 :class:`stoma.JSONResponseSpec`，
    ``False`` 对应 :class:`stoma.RawResponseSpec`。

    :var attr_name: 类属性名（如 ``on_200`` / ``on_4xx`` / ``on_200_application_json``）。
    :vartype attr_name: str
    :var status_code: 状态码显示值——精确匹配为 ``int``，通配符为原始 OpenAPI 字符串
        （``"default"`` / ``"4XX"`` / ``"5XX"`` / ``"1XX"`` / ``"2XX"`` / ``"3XX"``）。
    :vartype status_code: int | str
    :var status_matcher: 运行时校验谓词——精确匹配为 ``int``，
        通配符为 :func:`make_range_matcher` 生成的 ``Callable[[int], bool]``，
        ``default`` 为 ``lambda s: True``。
    :vartype status_matcher: int | Callable[[int], bool]
    :var media_type: 期望的 media type 字符串（如 ``application/json``）。
    :vartype media_type: str
    :var model_name: 引用的 model 类名（JSON 路径含 ``$ref`` 或 inline）；
        Raw 响应（non-JSON media type）为 ``None``。
    :vartype model_name: str | None
    :var is_json: ``True`` → :class:`stoma.JSONResponseSpec`；``False`` → :class:`stoma.RawResponseSpec`。
    :vartype is_json: bool
    :var spec_class: 模板渲染时使用的 spec 类名字符串——``is_json=True`` 时为
        ``"JSONResponseSpec"``；``is_json=False`` 时为下标化的
        ``"RawResponseSpec[bytes]"`` 或 ``"RawResponseSpec[str]"``（作为 ClassVar
        类型注解；裸 :class:`RawResponseSpec` 必须显式指定 ``T``，
        Wave 1.3 设计约束）。
    :vartype spec_class: str
    :var raw_factory: 仅 ``is_json=False`` 时有值——``"bytes"`` 或 ``"text"``，
        对应 :meth:`RawResponseSpec.bytes` / :meth:`RawResponseSpec.text` 工厂方法名；
        ``is_json=True`` 时为 ``None``。模板据此选择工厂方法而非下标构造，
        与用户调用点风格一致（plan 要求 factory methods for raw）。
    :vartype raw_factory: str | None
    :var status_code_or_matcher: 已渲染为代码生成字符串的 ``status_code`` 字面量——
        精确匹配为 ``"status_code=200"``；``"default"`` 为 ``"callable=lambda s: True"``；
        ``"4XX"`` 等范围键为 ``"callable=lambda s: 400 <= s < 500"``。模板直接嵌入，
        不再加 ``status_code=`` 前缀。
    :vartype status_code_or_matcher: str
    """

    attr_name: str
    status_code: int | str
    status_matcher: int | Callable[[int], bool]
    media_type: str
    model_name: str | None
    is_json: bool
    spec_class: str
    raw_factory: str | None
    status_code_or_matcher: str


def make_range_matcher(start: int, end: int) -> Callable[[int], bool]:
    """构造一个状态码范围谓词。

    返回的谓词 ``f`` 满足 ``f(s) == True`` 当且仅当 ``start <= s < end``。
    用于将 OpenAPI 通配符状态码（``4XX`` / ``5XX`` / ``1XX`` / ``2XX`` / ``3XX``）
    转换为 :class:`BaseResponseSpec` 子类可消费的 ``Callable[[int], bool]``。

    :param start: 范围起始（含）。
    :param end: 范围结束（不含）。
    :return: 谓词函数 ``lambda s: start <= s < end``。
    """
    return lambda s: start <= s < end


def render_status_code_kwarg(status_code: int | str) -> str:
    """将 ``status_code`` 渲染为 ``JSONResponseSpec(...)`` / ``RawResponseSpec(...)`` 的关键字参数片段。

    输出已含参数名（``status_code=`` / ``callable=``），模板直接嵌入，无需再加前缀。
    三类形态：

    - 精确匹配 ``int``（如 ``200``）→ ``"status_code=200"``。
    - OpenAPI ``"default"`` → ``"callable=lambda s: True"``。
    - 范围通配符 ``"1XX"`` / ``"2XX"`` / ``"3XX"`` / ``"4XX"`` / ``"5XX"``
      → ``"callable=lambda s: 400 <= s < 500"`` 等。

    :param status_code: 精确匹配为 ``int``；通配符为 OpenAPI 字符串
        （``"default"`` / ``"NXX"``）。
    :return: 可直接嵌入模板的代码片段字符串。
    :raise ValueError: ``status_code`` 既非 ``int``、也非 ``"default"``、也不在
        ``"NXX"`` 范围集合（无法静态推导 lambda 体）。
    """
    if isinstance(status_code, int):
        return f"status_code={status_code}"
    if status_code == "default":
        return "callable=lambda s: True"
    upper = status_code.upper()
    if len(upper) == 3 and upper[1:] == "XX" and upper[0] in "12345":
        digit = int(upper[0])
        return f"callable=lambda s: {digit * 100} <= s < {digit * 100 + 100}"
    msg = f"Cannot render status_code {status_code!r} to code-generation kwarg"
    raise ValueError(msg)


# 文本族 media type —— 响应 body 可用 ``response.text()`` 安全解码为 ``str``。
# 大小写不敏感（OpenAPI 3.1 规范允许大小写自由，但 ``_assert_media_type``
# 在 :class:`BaseResponseSpec` 内部统一 lowercased 比较）。
_TEXT_LIKE_MEDIA_TYPES: frozenset[str] = frozenset(
    {
        "application/xml",
        "application/yaml",
        "application/javascript",
        "application/x-www-form-urlencoded",
        "application/json-seq",
    }
)


def categorize_raw_media_type(media_type: str) -> Literal["bytes", "str"]:
    """把非 JSON media type 分类为 ``"bytes"`` 或 ``"str"``，决定 RawResponseSpec 的 ``T``。

    Wave 1.3 设计要求 :class:`stoma.RawResponseSpec` 必须显式指定 ``T``
    （``bytes`` 或 ``str``），否则裸 ``RawResponseSpec(...)`` 抛 :class:`TypeError`。
    渲染器按 media type 的可解码性派生 ``T``，避免在生成的代码里
    出现裸 ``RawResponseSpec(status_code=..., media_type=...)`` 形式的
    运行时崩溃。

    返回值是类型参数名（``"bytes"`` / ``"str"``）而非工厂方法后缀
    （``"bytes"`` / ``"text"``）——``spec_class`` 直接拼成
    ``"RawResponseSpec[<T>]"`` 形式（ClassVar 类型注解），
    工厂调用在模板里通过 ``"RawResponseSpec." + raw_factory`` 派生，
    由 :attr:`ResponseSpecDecl.raw_factory` 提供（``"bytes"`` / ``"text"``）。

    分类规则（大小写不敏感，优先文本族 fallback 到字节族）：

    - 文本族（→ ``"str"`` / :meth:`RawResponseSpec.text`）：

      - 所有 ``text/*``（``text/plain`` / ``text/html`` / ``text/xml`` /
        ``text/csv`` / ``text/yaml`` / ``text/event-stream`` 等）；
      - 显式白名单的 ``application/xml`` / ``application/yaml`` /
        ``application/javascript`` / ``application/x-www-form-urlencoded`` /
        ``application/json-seq``。

    - 字节族（→ ``"bytes"`` / :meth:`RawResponseSpec.bytes`，默认）：

      - 其他所有未列入文本族的 ``application/*``（含
        ``application/octet-stream`` / ``application/pdf``）；
      - ``image/*`` / ``audio/*`` / ``video/*``；
      - ``*/*`` 通配（spec 模糊声明时的兜底，保守取 bytes）。

    ``is_json_media_type`` 已经在调用方过滤 JSON 家族（含 ``application/json``
    与 ``application/*+json``），此处不重复判断——传入的 ``media_type`` 一定
    非 JSON。

    :param media_type: OpenAPI responses content 的 media type 字符串。
    :return: ``"str"`` 或 ``"bytes"``，对应
        :class:`RawResponseSpec` 的 ``T`` 类型参数。
    """
    normalized = media_type.strip().lower()
    # 文本族前缀匹配（text/* 全家）；常见文本 MIME 均落在此分支。
    if normalized.startswith("text/"):
        return "str"
    # 文本族白名单 application/* 子集；剥离 ``;charset=...`` 等参数再做精确匹配。
    main_type = normalized.split(";", 1)[0].strip()
    if main_type in _TEXT_LIKE_MEDIA_TYPES:
        return "str"
    # 兜底 bytes：image/* / audio/* / video/* / application/octet-stream /
    # application/pdf / */* 通配。保守取 bytes 因多数非文本资源都需要
    # ``response.body()`` 读取（Playwright 默认行为）。
    return "bytes"


def raw_factory_for(type_arg: Literal["bytes", "str"]) -> Literal["bytes", "text"]:
    """把 :func:`categorize_raw_media_type` 返回的 ``T`` 名映射到 :class:`RawResponseSpec` 工厂方法后缀。

    模板渲染时对 Raw 路径用 ``"RawResponseSpec." + raw_factory`` 拼出工厂调用：
    ``T="bytes"`` → ``RawResponseSpec.bytes(...)``，
    ``T="str"`` → ``RawResponseSpec.text(...)``。两个映射不同名是 Wave 1.3
    工厂方法设计的副作用——``text`` 强调「按文本解码」，``bytes`` 强调「按字节
    读取」，比 ``str(...)`` / ``bytes(...)`` 更直观。

    :param type_arg: :func:`categorize_raw_media_type` 返回的 ``T`` 类型名。
    :return: 工厂方法后缀，``"bytes"`` 仍为 ``"bytes"``，``"str"`` 映射为 ``"text"``。
    """
    if type_arg == "bytes":
        return "bytes"
    return "text"


class EndpointRenderer[ReferenceT: _ReferenceLike]:
    """Endpoint 路由文件渲染器（按 spec 版本注入 Reference 类型）。

    类型参数 ``ReferenceT`` 在构造时由关键字参数 ``Reference`` 决定：
    3.0 → ``Reference30``，3.1 → ``Reference31``。通常通过
    :func:`make_endpoint_renderer` 工厂创建，工厂返回 ``EndpointRenderer[Any]``，
    调用方无需关心具体版本。

    渲染过程中遇到的非致命问题（多 media type、Response 模型缺失）以及致命问题
    （spec 形态不被支持）统一收集到 :attr:`errors`，由调用方（``cli.make``）
    按 :class:`GenerationErrorKind` 分组打印并决定 exit code——只有
    ``SCHEMA_UNSUPPORTED``（实际未生成 route 文件）才触发非零退出。

    :var Reference: 实例化时注入的 Reference 类，用于在 ``object`` 上做
        版本感知的 Reference ``isinstance`` 检测。
    :vartype Reference: type[ReferenceT]
    :var template_dir: Jinja2 模板所在目录。
    :vartype template_dir: Path
    :var env: 已加载模板目录的 Jinja2 环境。
    :vartype env: jinja2.Environment
    :var errors: 渲染过程中收集的错误记录（按 :class:`GenerationErrorKind` 分类）。
    :vartype errors: list[GenerationError]
    """

    def __init__(
        self,
        *,
        Reference: type[ReferenceT],  # noqa: N803
        template_path: str | Path | None = None,
    ) -> None:
        """初始化渲染器。

        :param Reference: 该 spec 版本对应的 Reference 类（构造时传入，
            通常由 :func:`make_endpoint_renderer` 选择）。
        :param template_path: 模板目录路径，默认为 ``openapi/templates/``。
        """
        self.Reference = Reference
        if template_path is None:
            template_path = Path(__file__).parent / "templates"
        self.template_dir = Path(template_path)
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        # 统一错误汇：soft warning（多 media type / 缺 Response 模型）
        # 与 hard failure（spec 不被支持）通过 kind 区分；cli 在末尾按 kind 分组打印。
        self.errors: list[GenerationError] = []
        # 由 cli 在生成 models.py 后注入可用 class 名字集合
        # 若为 None 则不检查（向后兼容）
        self.available_models: set[str] | None = None

    def render(self, endpoint: Endpoint[Any, Any, Any]) -> tuple[str, str]:
        """渲染 endpoint 的 route.py 内容。

        一并返回从 operationId 派生的文件名（``{snake_case_id}.py``），
        与渲染结果对应——调用方（``make``）拿到 file_name 直接落盘，
        不用再算一次。

        响应声明处理流程：

        1. 调用 :meth:`_extract_response_specs` 取得按 ``status + media_type`` 切分的
           :class:`ResponseSpecDecl` 列表，覆盖每个合法响应分支（含 ``default`` /
           ``1XX``/``2XX``/``3XX``/``4XX``/``5XX`` 通配符及多 media type）。
        2. ``imported_models`` 从 decls 的 ``model_name`` 派生（Raw 响应的
           ``model_name=None`` 跳过），按 spec 顺序去重。
        3. ``imported_specs`` 按 decls 的 ``is_json`` 标志决定是否添加
           ``"JSONResponseSpec"`` 或 ``"RawResponseSpec"``——只要对应类型至少
           一条 decl 存在即添加，按 JSON → Raw 顺序。
        4. ``uses_classvar_import`` 任意 decl 存在时为 True，供模板按需注入
           ``from typing import ClassVar``。

        :param endpoint: :class:`Endpoint` IR 对象，类型参数用 ``Any``
            表达（renderer 不依赖具体 spec 版本类型）。
        :return: ``(file_name, rendered_code)`` 元组，``file_name`` 含
            ``.py`` 后缀。
        """
        operation_id = endpoint.operation_id
        class_name = to_pascal_case(operation_id)
        file_name = f"{to_snake(operation_id)}.py"
        response_spec_decls = self._extract_response_specs(endpoint.responses, endpoint)

        # 响应在前、请求体在后（保持 spec 顺序）；``dict.fromkeys`` 保序去重，避免重名重复 import。
        # response model 名字从 decls 的 ``model_name`` 派生（Raw 响应 ``model_name=None`` 跳过），
        # request body 的 ``import_model`` 追加到末尾并一起去重。
        body_fields_template = self._extract_request_body_info(endpoint.request_body, endpoint)
        header_fields, param_fields, uses_field_import = make_param_fields(endpoint.parameters)

        body_import_model: str | None = (
            body_fields_template.import_model if isinstance(body_fields_template, JSONRequestBodyFields) else None
        )
        imported_models: list[str] = list(
            dict.fromkeys(decl.model_name for decl in response_spec_decls if decl.model_name is not None)
        )
        if body_import_model:
            imported_models.append(body_import_model)
        imported_models = list(dict.fromkeys(imported_models))

        # ``imported_specs`` 按 decls 的 ``is_json`` 决定，按 JSON → Raw 顺序添加。
        # 模板据此条件导入 ``JSONResponseSpec`` / ``RawResponseSpec``。
        imported_specs: list[str] = []
        if any(decl.is_json for decl in response_spec_decls):
            imported_specs.append("JSONResponseSpec")
        if any(not decl.is_json for decl in response_spec_decls):
            imported_specs.append("RawResponseSpec")

        # 任意响应声明存在 → 模板按需导入 ``from typing import ClassVar``。
        uses_classvar_import = bool(response_spec_decls)

        # 把 body fields 子类拍平为 template 变量。
        # NONE 路径返回空字典时模板所有 body 块跳过。
        body_template_vars = flatten_body_fields(body_fields_template)

        # 仅 binary body 需要 renderer 派生 Content-Type header field
        # （Playwright 无法从裸字节推断）。scalar body 通过 ``Body(media_type=...)``
        # 路径传递 Content-Type，由 client 通过 ``param_info.media_type`` 派生。
        # 其他类型 Content-Type 由 Playwright 根据 body 形态自动设置，renderer 不干预；
        # 用户在 APIRoute 中显式提供的 Content-Type header field 仍由
        # :func:`serialize_header_params` 透传给 Playwright。
        content_type_header = build_content_type_header(header_fields, body_template_vars["media_type"])
        if content_type_header is not None:
            header_fields.append(FieldDecl(line=content_type_header))
            uses_field_import = uses_field_import or not is_snake_case("Content-Type")

        # body 字段（非 snake_case 时含 ``Field(serialization_alias=)``）也会触发 Field import。
        # 检查 4 类 body 字段字符串中是否含 ``Field(``，避免 multipart 纯文件场景漏 import。
        uses_field_import = uses_field_import or is_body_fields_use_field(body_template_vars)

        template: Template = self.env.get_template("endpoint.py.jinja2")
        module_docstring = build_endpoint_docstring(
            endpoint.summary, endpoint.description, operation_id=endpoint.operation_id
        )
        class_docstring = build_endpoint_docstring(endpoint.summary, endpoint.description)
        has_class_body_content = bool(
            param_fields
            or header_fields
            or body_template_vars.get("import_model")
            or body_template_vars.get("scalar_field")
            or body_template_vars.get("binary_file_field")
            or body_template_vars.get("form_text_fields")
            or body_template_vars.get("form_file_fields")
        )
        rendered_code = template.render(
            operation_id=endpoint.operation_id,
            class_name=class_name,
            method=endpoint.method.lower(),
            path=endpoint.path,
            summary=endpoint.summary,
            description=endpoint.description,
            **body_template_vars,
            header_fields=header_fields,
            param_fields=param_fields,
            imported_models=imported_models,
            uses_field_import=uses_field_import,
            response_spec_decls=response_spec_decls,
            imported_specs=imported_specs,
            uses_classvar_import=uses_classvar_import,
            module_docstring=module_docstring,
            class_docstring=class_docstring,
            has_class_body_content=has_class_body_content,
        )
        return file_name, rendered_code

    def _extract_request_body_info(
        self,
        request_body: Any,
        endpoint: Endpoint[Any, Any, Any],
    ) -> RequestBodyFields | None:
        """按 spec 的 media type 分类请求体，返回对应 body fields 子类实例。

        TODO: 后续支持 ``oneOf`` / ``anyOf`` / ``allOf`` 顶层组合子 schema（目前仅 JSON 路径支持）。
        对于 multipart / urlencoded form，后续 Form() 通过支持 BaseModel 来实现，Union 多个 BaseModel 实现 oneOf/anyOf，
        allOf 通过继承 BaseModel 实现。

        7 步流程（顺序严格）：

        1. ``requestBody`` / ``content`` 为空 → 返回 ``None``。
        2. ``content`` 含多个 media type key → 抛 :class:`OpenAPISchemaError`。
        3. media type 是 ``application/json`` → :class:`JSONRequestBodyFields`
           （``$ref`` / inline object）或 :class:`ScalarRequestBodyFields`
           （primitive schema）。
        4. media type 是 ``multipart/form-data`` → 顶层 schema 含
           ``oneOf`` / ``anyOf`` / ``allOf`` key 则报错；否则
           :class:`MultipartFormRequestBodyFields`。
        5. media type 是 ``application/x-www-form-urlencoded`` → 顶层 schema 含
           ``oneOf`` / ``anyOf`` / ``allOf`` key 则报错；遍历 properties 时
           ``format=binary`` 字段 ``warnings.warn``；返回
           :class:`UrlencodedFormRequestBodyFields`。
        6. ``schema.type == "string" AND schema.format == "binary"``
           （不限 media type，含 ``image/png`` / ``application/octet-stream``）
           → :class:`BinaryRequestBodyFields`。
        7. 兜底 RAW（其他非 JSON / 非 form 文本类型）：
           primitive schema → :class:`ScalarRequestBodyFields`；
           否则报错。

        JSON 路径调用 :func:`get_expanded_schema_dict`
        从 ``request_body.content`` 拿原始 media_type_schema 并走 jsonref 展开
        （仅展开 ``$ref``，不影响 model_generator 已生成的 import——
        dmcg 阶段已完成）。

        :param request_body: :class:`RequestBody` 对象（来自 openapi-pydantic）。
        :param endpoint: 当前 :class:`Endpoint` IR 对象。
        :return: 5 种 body fields 子类之一的实例；NONE 路径返回 ``None``。
        :raise OpenAPISchemaError: 多 media type、schema 含 oneOf/anyOf/allOf key、
            或 schema 形态不支持。
        """
        if request_body is None:
            return None

        content = getattr(request_body, "content", None)
        if not isinstance(content, dict) or not content:
            return None

        if len(content) != 1:
            all_media_types = list(content.keys())
            media_type, _ = next(iter(content.items()))
            self.errors.append(
                GenerationError(
                    method=endpoint.method,
                    path=endpoint.path,
                    kind=GenerationErrorKind.MULTI_MEDIA_TYPE,
                    message=(
                        f"endpoint 有多个 media type，已静默使用 {media_type!r}（其他被忽略："
                        f"{', '.join(all_media_types)}）"
                    ),
                )
            )
        else:
            media_type, _ = next(iter(content.items()))

        # 直接从 endpoint.expanded_raw_request_body 导航到 schema（已经过 jsonref 展开）
        # 替代原 get_expanded_schema_dict(request_body, media_type) 调用
        if not endpoint.expanded_raw_request_body:
            return None

        expanded_schema_dict: dict[str, Any] | None = (
            endpoint.expanded_raw_request_body.get("content", {}).get(media_type, {}).get("schema")
        )

        # 空 schema {} 或 schema 缺失 → 不生成 body 字段
        # （如 api.rest.sh 的 GET /get 等端点 requestBody.content.application/json.schema={}）
        if not expanded_schema_dict:
            return None

        # 步骤 3：application/json 及 application/*+json（dmcg 处理顶层 oneOf/anyOf/allOf，无需组合子检查）
        if is_json_media_type(media_type):
            if is_primitive_schema_dict(expanded_schema_dict):
                return self._build_scalar_body(expanded_schema_dict, media_type)
            schema_model = get_media_type_schema(request_body, media_type)
            return self._build_json_body(endpoint, schema_model)

        # 非 JSON 路径统一调用一次组合子检查，覆盖 multipart / urlencoded / binary / 兜底 RAW。
        # 顶层 oneOf/anyOf/allOf 在非 JSON media type 下 renderer 无法静态推断 fields。
        if has_combinator(expanded_schema_dict):
            msg = (
                f"{media_type} request body schema with top-level oneOf/anyOf/allOf is not supported; "
                "use application/json with $ref + inline merge in the OpenAPI spec."
            )
            raise OpenAPISchemaError(msg)

        # 步骤 4：multipart/form-data
        if media_type == "multipart/form-data":
            return self._build_multipart_body(expanded_schema_dict)

        # 步骤 5：application/x-www-form-urlencoded
        if media_type == "application/x-www-form-urlencoded":
            return self._build_urlencoded_body(expanded_schema_dict)

        # 步骤 6：string + format=binary（不限 media type）
        if is_binary_schema_dict(expanded_schema_dict):
            return self._build_binary_body(media_type)

        # 步骤 7：兜底 RAW
        return self._build_scalar_body(expanded_schema_dict, media_type)

    def _build_json_body(
        self,
        endpoint: Endpoint[Any, Any, Any],
        schema_model: BaseModel | None,
    ) -> JSONRequestBodyFields:
        """根据 ``schema_model`` 派生 ``import_model``。

        ``schema_model`` 是 :func:`get_media_type_schema`
        返回的原始 Pydantic 模型（``Reference30`` / ``Reference31`` /
        ``Schema30`` / ``Schema31``）。用原始模型而不是 jsonref 展开后的 dict
        是因为 jsonref 会把 ``$ref`` 替换为 inline 内容，丢失 model 名信息。

        两种形态：

        - ``Reference`` → 取 ref 末段 PascalCase 化为 model 名。
        - 内联 object schema → 引用 dmcg 已生成的 ``<OpId>Request`` 模型。
        - primitive schema 不进入本方法（由 :meth:`_build_scalar_body` 处理）。

        :param endpoint: 当前 :class:`Endpoint` IR 对象。
        :param schema_model: 原始 Pydantic 模型，可能为 ``None``。
        :return: :class:`JSONRequestBodyFields`。
        """
        if schema_model is None:
            return JSONRequestBodyFields()

        if isinstance(schema_model, self.Reference):
            ref_path = str(schema_model.ref).rsplit("/", 1)[-1]
            return JSONRequestBodyFields(import_model=to_pascal_case(ref_path))

        # inline object schema → dmcg 已生成 ``<OpId>Request`` 模型。
        model_name = f"{to_pascal_case(endpoint.operation_id)}Request"
        return JSONRequestBodyFields(import_model=model_name)

    def _build_urlencoded_body(
        self,
        expanded_schema_dict: dict[str, Any] | None,
    ) -> UrlencodedFormRequestBodyFields:
        """构造 ``application/x-www-form-urlencoded`` 请求体渲染信息。

        遍历 ``properties``：

        - ``format == "binary"`` 时 ``warnings.warn(...)``（FastAPI Form 字段
          不接受 binary 内容），仍按普通 Form 字段渲染；
        - 其他 primitive 走 ``Annotated[T, Form()]``；
        - array 走 :func:`resolve_array_type` 派生 ``list[T]``；
        - 非 snake_case 字段名自动追加 ``Field(serialization_alias=...)``
          保留原名（:func:`build_form_field_line` 已处理）。

        每个 property 的 ``description`` / ``example`` / ``examples`` 也被提取并
        传给 :func:`stoma.openapi.fields.build_form_field_line`，模板按
        :class:`FieldDecl` 解包渲染字段 docstring（与 dmcg 1:1 对齐）。

        :param expanded_schema_dict: jsonref 展开后的 schema 字典，可能为 ``None``。
        :return: :class:`UrlencodedFormRequestBodyFields`。
        """
        form_text_fields: list[FieldDecl] = []
        if expanded_schema_dict is None:
            return UrlencodedFormRequestBodyFields(form_text_fields=form_text_fields)
        properties = expanded_schema_dict.get("properties") or {}
        for prop_name, prop_schema in properties.items():
            if not isinstance(prop_schema, dict):
                continue
            prop_format = prop_schema.get("schema_format", "") or prop_schema.get("format", "")
            prop_type = prop_schema.get("type", "str")
            if prop_format == "binary":
                warnings.warn(
                    (
                        f"urlencoded form field {prop_name!r} has format=binary; "
                        "FastAPI Form() will not accept binary content, "
                        "consider using multipart/form-data instead."
                    ),
                    UserWarning,
                    stacklevel=2,
                )
            if prop_type == "array":
                py_type = resolve_array_type(prop_schema)
            else:
                py_type = python_type_name(prop_type)
            form_text_fields.append(
                build_form_field_line(
                    prop_name,
                    py_type,
                    description=prop_schema.get("description"),
                    example=prop_schema.get("example"),
                    examples=prop_schema.get("examples"),
                )
            )

        return UrlencodedFormRequestBodyFields(form_text_fields=form_text_fields)

    def _build_multipart_body(
        self,
        expanded_schema_dict: dict[str, Any] | None,
    ) -> MultipartFormRequestBodyFields:
        """构造 ``multipart/form-data`` 请求体渲染信息。

        遍历 ``properties``：

        - ``format == "binary`` → ``<name>: UploadFile`` 进入 ``form_file_fields``；
        - 其他 primitive → ``<name>: Annotated[T, Form()]`` 进入 ``form_text_fields``。

        每个 property 的 ``description`` / ``example`` / ``examples`` 也被提取并
        传给对应 builder，模板按 :class:`FieldDecl` 解包渲染字段 docstring。

        :param expanded_schema_dict: jsonref 展开后的 schema 字典，可能为 ``None``。
        :return: :class:`MultipartFormRequestBodyFields`（无 content_type，Playwright 自动设置）。
        """
        form_text_fields: list[FieldDecl] = []
        form_file_fields: list[FieldDecl] = []
        if expanded_schema_dict is None:
            return MultipartFormRequestBodyFields(
                form_text_fields=form_text_fields,
                form_file_fields=form_file_fields,
            )
        for prop_name, prop_schema in expanded_schema_dict.get("properties", {}).items():
            if not isinstance(prop_schema, dict):
                continue
            prop_format = prop_schema.get("schema_format", "") or prop_schema.get("format", "")
            prop_type = prop_schema.get("type", "str")
            if prop_format == "binary":
                form_file_fields.append(
                    build_upload_file_field_line(
                        prop_name,
                        description=prop_schema.get("description"),
                        example=prop_schema.get("example"),
                        examples=prop_schema.get("examples"),
                    )
                )
                continue
            if prop_type == "array":
                py_type = resolve_array_type(prop_schema)
            else:
                py_type = python_type_name(prop_type)
            form_text_fields.append(
                build_form_field_line(
                    prop_name,
                    py_type,
                    description=prop_schema.get("description"),
                    example=prop_schema.get("example"),
                    examples=prop_schema.get("examples"),
                )
            )

        return MultipartFormRequestBodyFields(
            form_text_fields=form_text_fields,
            form_file_fields=form_file_fields,
        )

    @staticmethod
    def _build_binary_body(
        media_type: str,
    ) -> BinaryRequestBodyFields:
        """构造 binary 单文件 raw body 渲染信息。

        ``string + format=binary`` 的 schema 派生单一 ``body: UploadFile`` 字段。
        字段名固定为 ``body``（避免按 operationId 派生导致非 snake_case 时需要
        ``Field(serialization_alias=...)`` 副作用）。对应 ``upload_as_multipart=False``
        （由 :class:`BinaryRequestBodyFields` 类型本身表达，:func:`flatten_body_fields`
        拍平时固定为 ``False``）。

        Binary body 的 schema 没有 description / example / examples 字段
        （OpenAPI 3.0 / 3.1 spec 均未声明——只有 ``string + format=binary``），
        所以 ``docstring`` 始终为 ``None``，但为保持与其它 body 字段的对齐语义
        （也通过 builder 派生 :class:`FieldDecl`），仍走
        :func:`stoma.openapi.fields.build_upload_file_field_line` 包装。

        :param media_type: 媒体类型字符串（用于 Content-Type header 派生）。
        :return: :class:`BinaryRequestBodyFields`。
        """
        binary_file_field = build_upload_file_field_line("body")
        return BinaryRequestBodyFields(
            binary_file_field=binary_file_field,
            media_type=media_type,
        )

    @staticmethod
    def _build_scalar_body(
        expanded_schema_dict: dict[str, Any] | None,
        media_type: str,
    ) -> ScalarRequestBodyFields:
        """构造 primitive schema 单字段 body 渲染信息。

        既覆盖 ``application/json`` 标量路径，也覆盖兜底 RAW 路径（``text/plain``
        / ``application/xml`` 等非 JSON / 非 form / 非 binary 媒体类型）。
        字段名固定为 ``body``（避免按 operationId 派生导致非 snake_case 时需要
        ``Field(serialization_alias=...)`` 副作用）。

        ``media_type`` 嵌入 ``Body(media_type=...)``，由 client 通过
        ``param_info.media_type`` 派生 Content-Type header——不走 Header field 路径，
        因为 scalar body 用 ``Body()`` 路径而非 ``Header()`` 路径传递 Content-Type。

        schema 的 ``description`` / ``example`` / ``examples`` 也被提取并传入
        :func:`stoma.openapi.fields.build_scalar_body_line`，由 builder 派生字段
        docstring（与 dmcg 1:1 对齐）。

        :param expanded_schema_dict: 展开后的 schema 字典，可能为 ``None``。
        :param media_type: 媒体类型字符串，嵌入 ``Body(media_type=...)``。
        :return: :class:`ScalarRequestBodyFields`。
        :raise OpenAPISchemaError: schema 不是 primitive 类型（兜底 RAW 场景下）。
        """
        if expanded_schema_dict is None:
            return ScalarRequestBodyFields()
        schema_type = expanded_schema_dict.get("type", "str")
        if not is_primitive_json_type(schema_type):
            msg = (
                f"Unsupported RAW body schema type: {schema_type!r}. "
                "Only primitive types (string/integer/number/boolean) are supported in non-JSON media types."
            )
            raise OpenAPISchemaError(msg)
        py_type = python_type_name(str(schema_type))
        scalar_field = build_scalar_body_line(
            py_type,
            media_type,
            description=expanded_schema_dict.get("description"),
            example=expanded_schema_dict.get("example"),
            examples=expanded_schema_dict.get("examples"),
        )
        return ScalarRequestBodyFields(scalar_field=scalar_field)

    @staticmethod
    def _parse_status_key(
        status_key: str,
    ) -> tuple[str, int | str, int | Callable[[int], bool]]:
        """解析 OpenAPI 状态码 key 为 ``(attr_base, status_code, matcher)``。

        状态码分三类：

        - ``"default"`` → ``attr_base="on_default"``、``status_code="default"``、
          ``matcher=lambda s: True``。
        - 通配符 ``"1XX"`` / ``"2XX"`` / ``"3XX"`` / ``"4XX"`` / ``"5XX"``
          （大小写不敏感）→ ``attr_base="on_4xx"`` 等（小写）、
          ``status_code="4XX"`` 等（保留大写原始键）、``matcher=make_range_matcher(400, 500)``。
        - 3 位数字（``"200"`` / ``"404"`` / ``"201"`` 等）→ ``attr_base="on_200"``、
          ``status_code=200``、``matcher=200``。

        :param status_key: OpenAPI responses 字典的 key 字符串。
        :return: 三元组 ``(attr_base, status_code, status_matcher)``。
        :raise ValueError: 状态码既非 ``default``、也不在通配符集合、也不是 3 位数字。
        """
        if status_key == "default":
            return "on_default", "default", (lambda s: True)
        upper = status_key.upper()
        if len(upper) == 3 and upper[1:] == "XX" and upper[0] in "12345":
            digit = int(upper[0])
            return f"on_{digit}xx", upper, make_range_matcher(digit * 100, digit * 100 + 100)
        code = int(status_key)
        return f"on_{code}", code, code

    def _extract_response_specs(
        self,
        responses: dict[str, Any] | None,
        endpoint: Endpoint[Any, Any, Any],
    ) -> list[ResponseSpecDecl]:
        """按 ``status_code + media_type`` 提取响应声明列表。

        与旧 :meth:`_get_json_response_types` 的关键差异：

        - **遍历所有 media type**，而非只取每个 status 的第一个 JSON 家族 media type。
          200 同时声明 ``application/json`` + ``application/problem+json`` 时会生成 2 条 decl。
        - 每条 decl 同时携带 ``is_json`` 标志与 ``model_name``（Raw 响应 ``model_name=None``），
          模板按此分别渲染 :class:`stoma.JSONResponseSpec` 与
          :class:`stoma.RawResponseSpec`。
        - Raw 路径额外派生 ``spec_class``（``"RawResponseSpec[bytes]"`` /
          ``"RawResponseSpec[str]"``，作为 ClassVar 类型注解）与 ``raw_factory``
          （``"bytes"`` / ``"text"``，对应 :meth:`RawResponseSpec.bytes` /
          :meth:`RawResponseSpec.text` 工厂方法）。Wave 1.3 设计禁止裸
          ``RawResponseSpec(...)`` 实例化（运行时抛 :class:`TypeError`），故
          渲染器按 :func:`categorize_raw_media_type` 静态分类 media type，避免
          生成可执行但运行时崩溃的代码。
        - ``attr_name`` 按该 response 的 media type 数量决定：
          单 media → ``on_<status>``；多 media → ``on_<status>_<sanitized_media>`` 消歧。
        - OpenAPI 通配符状态码（``default`` / ``4XX`` / ``5XX``）由
          :meth:`_parse_status_key` 转换为 ``Callable[[int], bool]`` 谓词或 lambda。
        - **去重保护**：同一 ``(status_key, media_type)`` 重复出现时跳过第二条并 emit
          :attr:`GenerationErrorKind.DUPLICATE_RESPONSE_SPEC` 警告
          （罕见但需处理，规范 dict 本身不允许 key 重复，但允许 dict 子类返回重复 items）。

        inline 对象命名沿用旧规则：第一个 ``{PascalOpId}Response``，第二个起
        ``{PascalOpId}Response1`` / ``{PascalOpId}Response2`` 等。
        ``$ref`` 取末段 PascalCase，与 :func:`to_pascal_case` 转换对齐 dmcg
        对 ``components.schemas`` key 的归一化。
        ``available_models`` 校验与 :attr:`GenerationErrorKind.MISSING_RESPONSE_MODEL`
        错误收集保留——仅对 JSON 路径生效。

        :param responses: OpenAPI 响应字典（状态码字符串 → Response 对象），可为 ``None`` 或空。
        :param endpoint: 当前 :class:`Endpoint` IR 对象。
        :return: :class:`ResponseSpecDecl` 列表，顺序与 OpenAPI spec 中 status 出现顺序一致；
            每个 status 内按 content 字典迭代顺序遍历 media type；无任何可声明响应时返回空列表。
        """
        if not responses:
            return []

        operation_id_pascal = to_pascal_case(endpoint.operation_id)
        inline_counter = 0
        decls: list[ResponseSpecDecl] = []
        seen: set[tuple[str, str]] = set()

        for status_key, response in responses.items():
            content = getattr(response, "content", None) or {}
            if not content:
                continue
            attr_base, status_code, status_matcher = self._parse_status_key(status_key)
            media_type_keys = list(content.keys())
            multi_media = len(media_type_keys) > 1

            for media_type, media_type_obj in content.items():
                dedup_key = (status_key, media_type)
                if dedup_key in seen:
                    self.errors.append(
                        GenerationError(
                            method=endpoint.method,
                            path=endpoint.path,
                            kind=GenerationErrorKind.DUPLICATE_RESPONSE_SPEC,
                            message=(f"重复响应声明 status={status_key!r}, media_type={media_type!r}，已跳过"),
                        )
                    )
                    continue
                seen.add(dedup_key)

                is_json = is_json_media_type(media_type)
                if multi_media:
                    attr_name = f"{attr_base}_{sanitize_media_type(media_type)}"
                else:
                    attr_name = attr_base

                schema = getattr(media_type_obj, "media_type_schema", None)
                model_name: str | None
                if isinstance(schema, self.Reference):
                    model_name = to_pascal_case(schema.ref.rsplit("/", 1)[-1])
                elif is_json:
                    inline_counter += 1
                    if inline_counter == 1:
                        model_name = f"{operation_id_pascal}Response"
                    else:
                        model_name = f"{operation_id_pascal}Response{inline_counter - 1}"
                else:
                    model_name = None

                if (
                    is_json
                    and model_name is not None
                    and self.available_models is not None
                    and model_name not in self.available_models
                ):
                    self.errors.append(
                        GenerationError(
                            method=endpoint.method,
                            path=endpoint.path,
                            kind=GenerationErrorKind.MISSING_RESPONSE_MODEL,
                            message=f"缺少 Response 模型 {model_name!r}（已跳过 import + generic）",
                        )
                    )
                    continue

                decls.append(
                    ResponseSpecDecl(
                        attr_name=attr_name,
                        status_code=status_code,
                        status_matcher=status_matcher,
                        media_type=media_type,
                        model_name=model_name,
                        is_json=is_json,
                        spec_class=(
                            "JSONResponseSpec"
                            if is_json
                            else f"RawResponseSpec[{categorize_raw_media_type(media_type)}]"
                        ),
                        raw_factory=None if is_json else raw_factory_for(categorize_raw_media_type(media_type)),
                        status_code_or_matcher=render_status_code_kwarg(status_code),
                    )
                )

        return decls


def make_endpoint_renderer(spec_version: SpecVersion) -> EndpointRenderer[Any]:
    """按 spec 版本构造对应的 :class:`EndpointRenderer`。

    工厂在初始化时把版本对应的 Reference 类（``Reference30`` 或
    ``Reference31``）注入到渲染器；之后渲染器内部在 ``object`` 上做版本感知
    收窄（``isinstance(schema, self.Reference)``），避免使用
    ``Reference30 | Reference31`` 联合类型。

    :param spec_version: spec 主版本，必须是 ``"3.0"`` 或 ``"3.1"``。
    :return: 与版本对应的 ``EndpointRenderer[Any]`` 实例（类型参数用 ``Any``
        让 ``render()`` 可接受任意版本的 Endpoint）。
    :raise ValueError: ``spec_version`` 不是 ``"3.0"`` / ``"3.1"`` 时。
    """
    if spec_version == "3.0":
        return EndpointRenderer(Reference=Reference30)
    if spec_version == "3.1":
        return EndpointRenderer(Reference=Reference31)
    msg = f"Unsupported spec_version: {spec_version!r}. Expected '3.0' or '3.1'."
    raise ValueError(msg)


def render_to_file(
    output_dir: str | Path,
    file_name: str,
    rendered_code: str,
    enable_ruff: bool = True,
) -> Path:
    """将渲染后的代码写入文件。

    ``file_name`` 由 ``EndpointRenderer.render()`` 一并返回（从
    ``operation_id`` 派生），本函数只负责落盘。

    :param output_dir: 输出目录。
    :param file_name: 目标文件名（含 ``.py`` 后缀）。
    :param rendered_code: 渲染后的 Python 代码。
    :param enable_ruff: 是否在写入后调用 ruff format + isort fix。默认为 True。
    :return: 写入的文件路径。
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    file_path = output_path / file_name
    file_path.write_text(rendered_code, encoding="utf-8")

    if enable_ruff and shutil.which("ruff") is not None:
        subprocess.run(
            ["ruff", "format", str(file_path)],
            check=False,
            capture_output=True,
            timeout=30,
        )
        subprocess.run(
            ["ruff", "check", "--select", "I,F401", "--fix", str(file_path)],
            check=False,
            capture_output=True,
            timeout=30,
        )

    return file_path
