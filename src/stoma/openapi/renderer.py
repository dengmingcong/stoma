"""Endpoint 路由文件渲染器。

把 OpenAPI 端点（:class:`src.openapi.models.Endpoint`）渲染成 ``route.py``
文件。**模型类由 ``datamodel-code-generator`` 在前置阶段生成**，本模块
只负责：

- 解析路径 / 查询 / 头部参数并渲染为 Pydantic 字段声明
- 解析请求体引用哪个模型（名字符串）
- 解析响应引用哪个模型（名字符串）
- 输出 ``from .models import ...`` 导入
- 输出响应声明为 ``@property`` 方法（每个 status 一个 spec 实例）
"""

from __future__ import annotations

import shutil
import subprocess
import warnings
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, NamedTuple, Protocol

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
    """

    MULTI_MEDIA_TYPE = "multi_media_type"
    MISSING_RESPONSE_MODEL = "missing_response_model"
    SCHEMA_UNSUPPORTED = "schema_unsupported"


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


class ResponseSpecDecl(NamedTuple):
    """单条响应声明（按 ``status_code + media_type`` 唯一）的渲染产物。

    由 :meth:`EndpointRenderer._extract_response_specs` 生成，供
    :mod:`stoma.openapi.templates.endpoint` 模板按
    ``@property def on_<attr_name>(self) -> <annotation>: return <class>(...)``
    形式输出。按 ``media_type`` 是否为 ``None`` 派生两条渲染路径：

    - ``media_type`` 非空（content 存在，可派生类型）→ :class:`stoma.ResponseSpec`，
      ``annotation`` 为 ``"ResponseSpec[<expected_type>]"``（如
      ``"ResponseSpec[int]"`` / ``"ResponseSpec[User]"``），
      模板拼装 ``ResponseSpec(status_code=..., media_type="<media_type>", expected_type=<expected_type>)``。
    - ``media_type`` 为空（无 content 或 schema 无法派生类型）→ :class:`stoma.EmptyResponseSpec`，
      ``annotation`` 为 ``"EmptyResponseSpec"``，``expected_type`` 为 ``None``，
      模板拼装 ``EmptyResponseSpec(status_code=...)``。

    状态码为 ``int`` 时模板输出 ``status_code=200``；
    为 lambda 源字符串（如 ``"lambda c: c not in [200]"``）时模板输出
    ``status_code=lambda c: ...``（lambda 前缀保留，模板不再走
    :func:`render_status_code_kwarg`，由模板条件分支直接拼装）。

    :var attr_name: ``@property`` 方法名（如 ``on_200`` / ``on_4xx`` /
        ``on_default`` / ``on_200_application_xml``）。
    :vartype attr_name: str
    :var annotation: ``@property`` 返回类型注解字符串——有 content 时为
        ``"ResponseSpec[<expected_type>]"``（如 ``"ResponseSpec[int]"`` /
        ``"ResponseSpec[User]"``），无 content 时为 ``"EmptyResponseSpec"``。
        IDE/mypy 通过下标解析出 ``T`` 后，
        ``response.expect(endpoint.on_200)`` 才能推断返回值的具体类型。
    :vartype annotation: str
    :var status_code: 状态码值——精确匹配为 ``int``，通配符为 lambda 源字符串
        （``"lambda c: c not in [200]"`` / ``"lambda c: 400 <= c < 500"``）。
        模板据此直接拼装 ``status_code=<int|lambda>``。
    :vartype status_code: int | str
    :var media_type: 期望的 media type 字符串（如 ``application/json`` /
        ``image/png``）。为 ``None`` 表示该 status code 无 content——
        走 :class:`stoma.EmptyResponseSpec` 路径。
    :vartype media_type: str | None
    :var expected_type: ``expected_type`` 参数的渲染值——有 content 时为类型
        字符串表达（标量 ``"int"`` / ``"float"`` / ``"str"`` / ``"bool"``、
        二进制 ``"bytes"``、对象模型名 ``"User"``），无 content 时为 ``None``。
    :vartype expected_type: str | None
    :var import_model: 需要在 route 文件中 ``from ..models import ...`` 的
        model 名（PascalCase 字符串）。仅场景 5（Reference）与场景 6
        （inline object）派发时填充，其他场景（Empty / primitive / binary）
        为 ``None``——这些场景的 ``expected_type`` 要么是 Python 内置类型
        （如 ``"int"`` / ``"bytes"``）要么是 ``None``，无需 import。模板不直接
        消费本字段，仅 :meth:`EndpointRenderer.render` 用于收集 ``imported``。
    :vartype import_model: str | None
    """

    attr_name: str
    annotation: str
    status_code: int | str
    media_type: str | None
    expected_type: str | None
    import_model: str | None = None


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

        1. 调用 :meth:`_extract_response_specs` 取得按 ``status + media_type``
           切分的 :class:`ResponseSpecDecl` 列表。
        2. ``imported`` 从 decls 的 ``import_model`` 派生：仅场景 5
           （Reference）与场景 6（inline object）填了该字段，其他场景为
           ``None`` 跳过；按 spec 顺序去重；body 字段的 ``import_model``
           追加到末尾并一起去重。
        3. ``imported_specs`` 按 decls 的 ``media_type is None`` 决定：
           ``media_type=None`` 的 decl（无 content 或 schema 无法派生类型）
           → ``"EmptyResponseSpec"`` 加入；``media_type`` 非空的 decl
           → ``"ResponseSpec"`` 加入。两类型同时存在按 Empty → Response
           顺序添加。
        4. 模板按 ``response_spec_decls`` 在 fields 之后输出 ``@property``
           方法，每个 decl 一条 ``on_<attr_name>`` 属性。

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
        # 对象 model 名字直接来自 decls 的 ``import_model`` 字段——仅场景 5
        # （Reference）与场景 6（inline object）派发时填充，其他场景（Empty /
        # primitive / binary）保持 ``None`` 跳过；request body 的
        # ``import_model`` 追加到末尾并一起去重。
        body_fields_template = self._extract_request_body_info(endpoint.request_body, endpoint)
        header_fields, param_fields, uses_field_import = make_param_fields(endpoint.parameters)

        body_import_model: str | None = (
            body_fields_template.import_model if isinstance(body_fields_template, JSONRequestBodyFields) else None
        )
        imported: list[str] = list(
            dict.fromkeys(decl.import_model for decl in response_spec_decls if decl.import_model is not None)
        )
        if body_import_model:
            imported.append(body_import_model)
        imported = list(dict.fromkeys(imported))

        # ``imported_specs`` 按 decls 的 ``media_type is None`` 决定，按 Empty → Response
        # 顺序添加。``media_type=None`` 的 decl（无 content 或 schema 无法派生类型）
        # 派生 ``EmptyResponseSpec``；其余 decl 派生 ``ResponseSpec``。模板据此条件
        # 导入 ``EmptyResponseSpec`` / ``ResponseSpec``。
        imported_specs: list[str] = []
        if any(decl.media_type is None for decl in response_spec_decls):
            imported_specs.append("EmptyResponseSpec")
        if any(decl.media_type is not None for decl in response_spec_decls):
            imported_specs.append("ResponseSpec")

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
            imported=imported,
            uses_field_import=uses_field_import,
            response_spec_decls=response_spec_decls,
            imported_specs=imported_specs,
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

    def _extract_response_specs(
        self,
        responses: dict[str, Any] | None,
        endpoint: Endpoint[Any, Any, Any],
    ) -> list[ResponseSpecDecl]:
        """按 6 场景派发提取响应声明列表。

        输出形态：每个状态码（无 content 时 1 条）或每个 ``(status_code, media_type)``
        组合（有 content 时）对应一条 :class:`ResponseSpecDecl`，
        模板按 ``@property def on_<attr_name>(self) -> <annotation>:
        return <constructor>(...)`` 形式输出。

        6 场景派发（实现顺序：binary 检测须先于 primitive——binary schema
        ``{"type":"string","format":"binary"}`` 的 ``type == "string"`` 同样命中
        primitive 集合，若不先短路会被误归为 ``ResponseSpec[str]``，丢失
        ``bytes`` 的 ``response.body()`` 直通路径）：

        1. **无 content**（``content is None or empty``）→ 1 条
           :class:`EmptyResponseSpec` decl，``media_type=None``、
           ``expected_type=None``、``annotation="EmptyResponseSpec"``。
        2. **有 content + schema 为 None / 空 Schema**（``schema.model_dump`` 退化
           为空 dict）→ :class:`EmptyResponseSpec` decl——schema 无法派生类型时
           兜底。
        3. **有 content + primitive schema**（``is_primitive_schema_dict``）→
           :class:`ResponseSpec` decl，``expected_type`` 按 ``type=integer/number/
           string/boolean`` 分别 ``"int"`` / ``"float"`` / ``"str"`` / ``"bool"``。
        4. **有 content + binary schema**（``is_binary_schema_dict``）→
           :class:`ResponseSpec` decl，``expected_type="bytes"``。
        5. **有 content + Reference** → :class:`ResponseSpec` decl，
           ``expected_type=<PascalCase(ref 末段)>``，走 ``available_models`` 校验。
        6. **有 content + inline object** → :class:`ResponseSpec` decl，
           ``expected_type={OpId}Response / {OpId}Response<n>``，
           走 ``available_models`` 校验。

        行为要点：

        - **每个 status code 都生成 decl**：包括无 content 的 status code（场景 1）、
          有 content 但 schema 为空的 status code（场景 2）——旧实现用
          ``if not content: continue`` 丢弃这些 status，导致 204 No Content 等
          端点无任何响应声明。新实现一律派发，避免丢失 status code 语义。
        - **``attr_name``** 按该 status 的 media type 数量决定：单 media →
          ``on_<status>``；多 media → ``on_<status>_<sanitized_media>`` 消歧。
        - **``inline_counter``** 仅在场景 6（inline 对象）增加；scalar / binary
          不消耗计数器，对齐 dmcg 的 ``{OpId}Response`` / ``{OpId}Response1``
          命名约定。
        - **``available_models`` 校验**仅作用于对象 schema（Reference + inline
          object，场景 5 + 6）——scalar Python 类型（``int`` / ``str`` /
          ``float`` / ``bool``）与 ``bytes`` 是内置类型，无需检查。
        - **OpenAPI 通配符状态码**（``default`` / ``4XX`` / ``5XX``）经
          :meth:`_parse_status_key` 转换为 lambda 源字符串；模板拼成
          ``status_code=lambda c: ...`` 形式（v2 :class:`stoma.BaseResponseSpec`
          ``status_code`` 字段已直接接受 Callable，不再需要 ``callable=`` 别名）。
        - **去重保护**：同一 ``(status_key, media_type)`` 重复出现时跳过第二条并
          发 ``UserWarning``（罕见但需处理——规范 ``dict`` 本身不允许 key 重复，
          但允许 dict 子类返回重复 items）。

        ``$ref`` 取末段 PascalCase，与 :func:`to_pascal_case` 转换对齐 dmcg
        对 ``components.schemas`` key 的归一化。

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

        # 收集同一 endpoint 中所有 int 状态码（不含 wildcard），供 default lambda 排除。
        int_status_codes: list[int] = []
        for status_key in responses:
            if status_key.isdigit() and len(status_key) == 3:
                int_status_codes.append(int(status_key))

        for status_key, response in responses.items():
            content = getattr(response, "content", None) or {}
            attr_base, status_code = self._parse_status_key(
                status_key,
                other_int_codes=int_status_codes,
            )

            # 场景 1：无 content（如 204 No Content）→ 派发 1 条 EmptyResponseSpec decl。
            if not content:
                decls.append(
                    ResponseSpecDecl(
                        attr_name=attr_base,
                        annotation="EmptyResponseSpec",
                        status_code=status_code,
                        media_type=None,
                        expected_type=None,
                        import_model=None,
                    )
                )
                continue

            media_type_keys = list(content.keys())
            multi_media = len(media_type_keys) > 1

            for media_type, media_type_obj in content.items():
                dedup_key = (status_key, media_type)
                if dedup_key in seen:
                    warnings.warn(
                        (
                            f"{endpoint.method} {endpoint.path}: "
                            f"重复响应声明 status={status_key!r}, media_type={media_type!r}，已跳过"
                        ),
                        UserWarning,
                        stacklevel=2,
                    )
                    continue
                seen.add(dedup_key)

                if multi_media:
                    attr_name = f"{attr_base}_{sanitize_media_type(media_type)}"
                else:
                    attr_name = attr_base

                schema = getattr(media_type_obj, "media_type_schema", None)

                # 场景 2：schema 缺失或为空 → EmptyResponseSpec 兜底。
                if schema is None or (
                    hasattr(schema, "model_dump")
                    and not schema.model_dump(mode="json", exclude_none=True)
                ):
                    decls.append(
                        ResponseSpecDecl(
                            attr_name=attr_name,
                            annotation="EmptyResponseSpec",
                            status_code=status_code,
                            media_type=None,
                            expected_type=None,
                            import_model=None,
                        )
                    )
                    continue

                # 场景 3 + 4：primitive / binary 检测需要 schema 的 dict 形态。
                # Reference 的 dump 是 ``{'ref': '...'}``（不含 ``type`` / ``format``），
                # 不命中两种检测，正确落到场景 5。
                expanded = schema.model_dump(mode="json", exclude_none=True)

                # binary 必须先于 primitive 判定：
                # ``is_primitive_schema_dict`` 对 ``{"type":"string","format":"binary"}``
                # 也返回 True（``type == "string"`` 命中 primitive 集合），
                # 不先短路 binary 会把它误归为 ``ResponseSpec[str]``。
                # ``bytes`` 走 ``response.body()`` 路径而非 ``validate_json``。
                if is_binary_schema_dict(expanded):
                    decls.append(
                        ResponseSpecDecl(
                            attr_name=attr_name,
                            annotation="ResponseSpec[bytes]",
                            status_code=status_code,
                            media_type=media_type,
                            expected_type="bytes",
                            import_model=None,
                        )
                    )
                    continue

                # 场景 3：primitive scalar → ResponseSpec decl。
                if is_primitive_schema_dict(expanded):
                    expected_type = python_type_name(expanded["type"])
                    decls.append(
                        ResponseSpecDecl(
                            attr_name=attr_name,
                            annotation=f"ResponseSpec[{expected_type}]",
                            status_code=status_code,
                            media_type=media_type,
                            expected_type=expected_type,
                            import_model=None,
                        )
                    )
                    continue

                # 场景 5：Reference → ResponseSpec decl，``expected_type`` 为 ref 末段 PascalCase。
                if isinstance(schema, self.Reference):
                    model_name = to_pascal_case(schema.ref.rsplit("/", 1)[-1])
                    if (
                        self.available_models is not None
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
                            annotation=f"ResponseSpec[{model_name}]",
                            status_code=status_code,
                            media_type=media_type,
                            expected_type=model_name,
                            import_model=model_name,
                        )
                    )
                    continue

                # 场景 6：inline object → ResponseSpec decl。
                # 首个 inline 命名 ``{OpId}Response``，后续追加 ``1`` / ``2`` …，
                # 对齐 dmcg 的 ``components.schemas`` key 归一化约定。
                inline_counter += 1
                if inline_counter == 1:
                    model_name = f"{operation_id_pascal}Response"
                else:
                    model_name = f"{operation_id_pascal}Response{inline_counter - 1}"

                if (
                    self.available_models is not None
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
                        annotation=f"ResponseSpec[{model_name}]",
                        status_code=status_code,
                        media_type=media_type,
                        expected_type=model_name,
                        import_model=model_name,
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


__all__ = [
    "EndpointRenderer",
    "GenerationError",
    "GenerationErrorKind",
    "ResponseSpecDecl",
    "make_endpoint_renderer",
    "render_status_code_kwarg",
    "render_to_file",
]
