"""Endpoint 路由文件渲染器。

把 OpenAPI 端点（:class:`src.openapi.models.Endpoint`）渲染成 ``route.py``
文件。**模型类由 ``datamodel-code-generator`` 在前置阶段生成**，本模块
只负责：

- 解析路径 / 查询 / 头部参数并渲染为 Pydantic 字段声明
- 解析请求体引用哪个模型（名字符串）
- 解析响应引用哪个模型（名字符串）
- 输出 ``from .models import ...`` 导入

版本感知
========

OpenAPI 3.0 和 3.1 的 ``Reference`` 在 openapi-pydantic 里是互相独立的
类（没有继承关系），用 ``Reference30 | Reference31`` 联合类型无法做
``isinstance`` 检测。本模块的做法：

- :class:`EndpointRenderer` 是带类型参数 ``ReferenceT`` 的泛型类，构造时
  通过关键字参数 ``Reference`` 注入版本对应的 Reference 类
  （``Reference30`` 或 ``Reference31``）；``ReferenceT`` 上界为结构化
  Protocol :class:`_ReferenceLike`（要求 ``ref: str`` 字段），这样
  ``mypy --strict`` 下 :meth:`_is_reference` 的 ``TypeGuard`` 收窄才能在
  True 分支看到 ``schema.ref``（``BaseModel`` 纯上界不带 ``ref`` 字段）；
- :func:`make_endpoint_renderer` 工厂按 spec 版本选择 Reference 类并构造
  渲染器，返回 ``EndpointRenderer[Any]``，调用方无需关心具体版本；
- 渲染器内部用 :meth:`EndpointRenderer._is_reference` 在 ``object`` 上做
  ``TypeGuard`` 收窄——True 分支把 schema 收窄到 ``ReferenceT``，可安全
  访问 ``schema.ref``。

所有 schema → model 转换都在 :mod:`src.openapi.parser` 的 ``load()``
阶段（用 openapi-pydantic 构造 Pydantic 模型，``$ref`` 字段会被填充为
版本对应的 Reference 实例）。renderer 直接读 ``Reference.ref`` 字符串
计算模型名。
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, TypeGuard

import jsonref
from jinja2 import Environment, FileSystemLoader, Template
from pydantic.alias_generators import to_snake

from src.client import RequestBodyKind
from src.openapi._naming import _is_snake_case, _to_field_name, _to_pascal_case
from src.openapi.models import Endpoint
from src.openapi.models_types import SpecVersion
from src.openapi.parser import OpenAPISchemaError
from src.openapi.reference_types import Reference30, Reference31


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


@dataclass
class RequestBodyFields:
    """请求体字段渲染信息的容器。

    按 :class:`src.client.RequestBodyKind` 派发后，各分支填充不同字段：

    - ``RAW``：``imported_models`` 填充 model 名字符串（``application/json``
      model body 路径），或 ``scalar_body_field`` 单字段字符串（标量
      JSON 路径）。template 渲染 ``body: <model>`` 或
      ``<field>: Annotated[<type>, Body()]``。
    - ``URLENCODED``：``form_fields`` 填充
      ``"<name>: Annotated[<type>, Form()]"`` 列表。
    - ``MULTIPART``：``form_fields`` / ``file_fields`` 分别填充。
    - ``BINARY``：单字段放进 ``scalar_body_field``，构造为
      ``"<name>: UploadFile"``，``upload_as_multipart=False``。
    - ``NONE``：全部字段保持默认值（template 跳过所有分支）。

    :var scalar_body_field: 单字段声明字符串（RAW scalar / BINARY）。
    :vartype scalar_body_field: str | None
    :var form_fields: form 字段声明字符串列表（URLENCODED / MULTIPART）。
    :vartype form_fields: list[str]
    :var file_fields: file 字段声明字符串列表（MULTIPART）。
    :vartype file_fields: list[str]
    :var upload_as_multipart: 是否以 ``multipart/form-data`` 传输（MULTIPART
        为 ``True``，BINARY 为 ``False``）。
    :vartype upload_as_multipart: bool
    :var imported_models: 待导入的模型名列表（RAW model 路径填充）。
    :vartype imported_models: list[str]
    :var body_kind: 请求体类型枚举（方便 template 做路由判断）。
    :vartype body_kind: RequestBodyKind
    :var content_type: 自动派生的 Content-Type header 字符串（无显式
        ``Content-Type`` 头时填充，用于保证 wire 上 Content-Type 与
        spec 一致）。
    :vartype content_type: str | None
    """

    scalar_body_field: str | None = None
    form_fields: list[str] = field(default_factory=list)
    file_fields: list[str] = field(default_factory=list)
    upload_as_multipart: bool = True
    imported_models: list[str] = field(default_factory=list)
    body_kind: RequestBodyKind = RequestBodyKind.NONE
    content_type: str | None = None


class EndpointRenderer[ReferenceT: _ReferenceLike]:
    """Endpoint 路由文件渲染器（按 spec 版本注入 Reference 类型）。

    类型参数 ``ReferenceT`` 在构造时由关键字参数 ``Reference`` 决定：
    3.0 → ``Reference30``，3.1 → ``Reference31``。通常通过
    :func:`make_endpoint_renderer` 工厂创建，工厂返回 ``EndpointRenderer[Any]``，
    调用方无需关心具体版本。

    :var Reference: 实例化时注入的 Reference 类，用于
        :meth:`_is_reference` 的 ``TypeGuard`` 检测。
    :vartype Reference: type[ReferenceT]
    :var template_dir: Jinja2 模板所在目录。
    :vartype template_dir: Path
    :var env: 已加载模板目录的 Jinja2 环境。
    :vartype env: jinja2.Environment
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

    def _is_reference(self, schema: object) -> TypeGuard[ReferenceT]:
        """TypeGuard：判断 schema 是否是当前版本对应的 Reference 实例。

        :param schema: 待检测的 schema（通常是 ``param.param_schema`` /
            ``media_type_schema``）。
        :return: ``True`` 时把 schema 收窄到 ``ReferenceT``，可在 True
            分支安全访问 ``schema.ref``。
        """
        return isinstance(schema, self.Reference)

    def render(self, endpoint: Endpoint[Any, Any, Any]) -> tuple[str, str]:
        """渲染 endpoint 的 route.py 内容。

        一并返回从 operationId 派生的文件名（``{snake_case_id}.py``），
        与渲染结果对应——调用方（``make``）拿到 file_name 直接落盘，
        不用再算一次。

        :param endpoint: :class:`Endpoint` IR 对象，类型参数用 ``Any``
            表达（renderer 不依赖具体 spec 版本类型）。
        :return: ``(file_name, rendered_code)`` 元组，``file_name`` 含
            ``.py`` 后缀。
        """
        operation_id = endpoint.operation_id
        class_name = _to_pascal_case(operation_id)
        file_name = f"{to_snake(operation_id)}.py"
        response_type = self._extract_response_info(endpoint.responses, endpoint)
        body_fields_template = self._extract_request_body_info(endpoint.request_body, endpoint)
        header_fields, param_fields, uses_field_import = self._extract_params(endpoint.parameters)

        # 响应在前、请求体在后（保持 spec 顺序）；``dict.fromkeys`` 保序去重，避免重名重复 import。
        # imported_models 来自 response_type + body_fields_template.imported_models。
        models_for_import: list[str] = list(response_type)
        models_for_import.extend(body_fields_template.imported_models)
        imported_models = list(dict.fromkeys(models_for_import))

        # request_body_type 保留字符串形式供 template 旧路径使用（JSON_MODEL → body: <Type>）。
        request_body_type = body_fields_template.imported_models[0] if body_fields_template.imported_models else ""

        # 当 _extract_request_body_info 自动派生 Content-Type（body_fields_template.content_type）且
        # 用户未显式声明同名 header field 时，注入一个 Annotated[str, Header()] 字段占位，
        # 避免与运行时派生的 Content-Type 冲突。
        content_type_header = self._build_content_type_header(
            header_fields, body_fields_template.content_type
        )
        if content_type_header is not None:
            header_fields.append(content_type_header)
            uses_field_import = uses_field_import or not _is_snake_case("Content-Type")

        template: Template = self.env.get_template("endpoint.py.jinja2")
        rendered_code = template.render(
            operation_id=endpoint.operation_id,
            class_name=class_name,
            method=endpoint.method.lower(),
            path=endpoint.path,
            summary=endpoint.summary,
            description=endpoint.description,
            response_type=response_type,
            request_body_type=request_body_type,
            scalar_body_field=body_fields_template.scalar_body_field,
            form_fields=body_fields_template.form_fields,
            file_fields=body_fields_template.file_fields,
            upload_as_multipart=body_fields_template.upload_as_multipart,
            header_fields=header_fields,
            param_fields=param_fields,
            imported_models=imported_models,
            uses_field_import=uses_field_import,
        )
        return file_name, rendered_code

    def _extract_params(
        self,
        parameters: list[Any],
    ) -> tuple[list[str], list[str], bool]:
        """提取参数信息（query/header/path），仍由 renderer 渲染为字段声明。

        :param parameters: OpenAPI 参数列表。
        :return: ``(Header 字段声明列表, Query/Path 字段声明列表, uses_field_import)``。
            ``uses_field_import`` 为 ``True`` 时表示存在至少一个非 snake_case
            参数，其字段声明会引用 ``Field(serialization_alias=...)``，
            渲染时需要在模板里加上 ``from pydantic import Field`` 导入。
        """
        header_fields: list[str] = []
        param_fields: list[str] = []
        uses_field_import = False

        for param in parameters:
            name = param.name or ""
            param_in = param.param_in
            location = param_in.value if param_in else "query"
            required = param.required or False
            schema = param.param_schema

            # 参数级 ``$ref`` 已在 :func:`src.openapi.parser.make_openapi_parser`
            # 上游通过 ``_expand_parameter_refs`` 展开为内联 schema，因此
            # ``schema`` 此时只会是普通 Schema（不会触发 ``_is_reference``）。
            schema_dict = schema.model_dump(mode="json") if schema else {}
            json_type = schema_dict.get("type", "Any")
            # 1.0 范围：仅支持原始类型作为参数，复杂 schema 应挪到 requestBody。
            if json_type not in {"string", "integer", "number", "boolean"}:
                msg = (
                    f"Unsupported schema type for parameter {name!r} ({location}): "
                    f"{json_type!r}. Only primitive types (string/integer/number/boolean) are supported."
                )
                raise OpenAPISchemaError(msg)
            param_type = _map_json_schema_type(str(json_type))

            if not _is_snake_case(name):
                uses_field_import = True

            field_line = _build_param_field_line(name, param_type, required, location)

            if location == "header":
                header_fields.append(field_line)
            else:
                param_fields.append(field_line)

        return header_fields, param_fields, uses_field_import

    def _extract_request_body_info(
        self,
        request_body: Any,
        endpoint: Endpoint[Any, Any, Any],
    ) -> RequestBodyFields:
        """按 runtime 的 :class:`RequestBodyKind` 分类请求体。

        流程（与 spec 的 media type 一一对应）：

        1. ``requestBody`` / ``content`` 为空 → :attr:`RequestBodyKind.NONE`。
        2. ``content`` 含多个 media type key → 抛出 :class:`OpenAPISchemaError`
           （stoma 不支持多 content type，runtime ``_serialize_body_params``
           只派发单一编码路径）。
        3. media type 是 ``application/json`` → :attr:`RequestBodyKind.RAW`，
           用 ``jsonref.replace_refs`` 展开 schema 后按 JSON body 渲染
           （$ref 解析后 ``_is_reference`` 才能正确收窄）。
        4. media type 是 ``multipart/form-data`` → :attr:`RequestBodyKind.MULTIPART_FORM`，
           遍历 ``properties``：``format == binary`` → ``<name>: UploadFile``，
           其他 primitive → ``<name>: Annotated[T, Form()]``。
        5. media type 是 ``application/x-www-form-urlencoded`` →
           :attr:`RequestBodyKind.URLENCODED_FORM`，遍历 ``properties``：
           primitive → ``Annotated[T, Form()]``，array → ``Annotated[list[T], Form()]``；
           发现 ``format == binary`` 属性 → ``warnings.warn(...)`` 提示
           FastAPI Form 字段不会接收 binary 内容。
        6. ``schema.type == "string" AND schema.format == "binary"``（不限
           media type，例如 ``image/png`` / ``application/octet-stream``）→
           :attr:`RequestBodyKind.BINARY` + ``upload_as_multipart=False``，
           渲染为 ``<name>: UploadFile``。
        7. 其他非 JSON media type（如 ``text/plain``）→ :attr:`RequestBodyKind.RAW`
           fallback，按模型名或 ``<field>: Body()`` 渲染。

        .. note::
           命中具体 media type（含 JSON / multipart / urlencoded / BINARY）
           时填充 ``RequestBodyFields.content_type``，由
           :meth:`render` 检测 endpoint 是否已有显式 ``Content-Type`` header
           字段，没有时自动追加，确保运行时发送的 Content-Type 与 spec 一致。

        :param request_body: :class:`RequestBody` 对象（来自 openapi-pydantic）。
        :param endpoint: 当前 :class:`Endpoint` IR 对象。
        :return: :class:`RequestBodyFields` 结构。
        """
        if request_body is None:
            return RequestBodyFields(body_kind=RequestBodyKind.NONE)

        content = getattr(request_body, "content", None)
        if not isinstance(content, dict) or not content:
            return RequestBodyFields(body_kind=RequestBodyKind.NONE)

        if len(content) != 1:
            msg = f"Multiple media types in requestBody not supported: {list(content.keys())}"
            raise OpenAPISchemaError(msg)

        media_type, media_type_obj = next(iter(content.items()))
        schema = getattr(media_type_obj, "media_type_schema", None)

        if media_type == "application/json":
            return self._build_json_body(schema, media_type, endpoint)
        if media_type == "multipart/form-data":
            return self._build_form_body(schema, media_type, is_multipart=True)
        if media_type == "application/x-www-form-urlencoded":
            return self._build_form_body(schema, media_type, is_multipart=False)

        if schema is not None:
            schema_dict = schema.model_dump(mode="json")
            if schema_dict.get("type") == "string" and (
                schema_dict.get("schema_format", "") or schema_dict.get("format", "")
            ) == "binary":
                field_name = _to_field_name(endpoint.operation_id)
                return RequestBodyFields(
                    scalar_body_field=f"{field_name}: UploadFile",
                    upload_as_multipart=False,
                    body_kind=RequestBodyKind.BINARY,
                    content_type=media_type,
                )

        return self._build_raw_body(schema, media_type, endpoint)

    def _build_json_body(
        self,
        schema: Any,
        media_type: str,
        endpoint: Endpoint[Any, Any, Any],
    ) -> RequestBodyFields:
        """构造 application/json 请求体渲染信息。

        media_type 已被前置 ``_extract_request_body_info`` 判定为
        ``application/json``；此处只负责 schema 形态分流：

        - ``$ref`` 指向 ``components.schemas.*`` → 取末段 PascalCase 化为 model 名。
        - 内联 object schema（dmcg 已生成对应 ``<OpId>Request`` 模型）→ 引用之。
        - primitive schema → ``<field>: Annotated[<type>, Body()]`` 标量 body。
          字段名按 :func:`_to_field_name` 从 operationId 派生（snake_case 化），
          对齐老 parser 行为。

        jsonref 展开只影响 ``_is_reference`` 的 ``TypeGuard`` 收窄——
        model 已经在 model_generator 阶段生成完毕，import 也已固定。
        这里用 ``jsonref.replace_refs`` 把 ``$ref`` 替换为内联 schema，
        再走 ``_is_reference`` 检测。

        :param schema: application/json 的 media_type_schema 节点。
        :param media_type: 媒体类型字符串（``"application/json"``）。
        :param endpoint: 当前 :class:`Endpoint` IR 对象。
        :return: :class:`RequestBodyFields`。
        """
        if schema is None:
            return RequestBodyFields(
                body_kind=RequestBodyKind.RAW,
                content_type=media_type,
            )

        # model_generator 阶段已固定 import 集；此处 jsonref 展开只影响
        # ``_is_reference`` 的 TypeGuard 收窄，让 $ref 形态的 schema 走对分支。
        try:
            resolved = jsonref.replace_refs(schema.model_dump(mode="json"), proxies=False, lazy_load=False)
        except Exception:
            resolved = None

        if isinstance(resolved, dict) and "$ref" in resolved:
            ref_path = str(resolved["$ref"])
            model_name = _to_pascal_case(ref_path.rsplit("/", 1)[-1])
            return RequestBodyFields(
                imported_models=[model_name],
                body_kind=RequestBodyKind.RAW,
                content_type=media_type,
            )

        if self._is_reference(schema):
            model_name = _to_pascal_case(schema.ref.rsplit("/", 1)[-1])
            return RequestBodyFields(
                imported_models=[model_name],
                body_kind=RequestBodyKind.RAW,
                content_type=media_type,
            )

        schema_dict = schema.model_dump(mode="json")
        schema_type = schema_dict.get("type", "")
        if schema_type in {"string", "integer", "number", "boolean"}:
            field_name = _to_field_name(endpoint.operation_id)
            py_type = _PYTHON_TYPE_MAP.get(schema_type, "str")
            return RequestBodyFields(
                scalar_body_field=f"{field_name}: Annotated[{py_type}, Body()]",
                body_kind=RequestBodyKind.RAW,
                content_type=media_type,
            )

        model_name = f"{_to_pascal_case(endpoint.operation_id)}Request"
        return RequestBodyFields(
            imported_models=[model_name],
            body_kind=RequestBodyKind.RAW,
            content_type=media_type,
        )

    def _build_form_body(
        self,
        schema: Any,
        media_type: str,
        *,
        is_multipart: bool,
    ) -> RequestBodyFields:
        """构造 form-urlencoded 或 multipart/form-data 请求体渲染信息。

        - multipart: ``format == "binary"`` 字段渲染为 ``<name>: UploadFile``
          （进入 ``file_fields``），其他 primitive 走 ``Annotated[T, Form()]``。
        - urlencoded: 全部 primitive 走 ``Annotated[T, Form()]``；发现
          ``format == "binary"`` 时 ``warnings.warn(...)``（不抛错，FastAPI
          Form 字段不支持 binary 内容，但不能让 codegen 失败）。

        字段名：``_to_field_name`` 处理 hyphen / 关键字 / 数字开头；
        渲染时若不是合法 snake_case，自动加 ``Field(serialization_alias=...)``
        保留原名——参考 :func:`_build_form_field_line` 的 snake_case 分支判定。

        :param schema: 对应 media type 的 media_type_schema 节点。
        :param media_type: 媒体类型字符串。
        :param is_multipart: True 表示 multipart/form-data，False 表示 urlencoded。
        :return: :class:`RequestBodyFields`。
        """
        if schema is None:
            return RequestBodyFields(
                body_kind=RequestBodyKind.MULTIPART_FORM if is_multipart else RequestBodyKind.URLENCODED_FORM,
                content_type=media_type,
            )
        schema_dict = schema.model_dump(mode="json")
        form_fields: list[str] = []
        file_fields: list[str] = []
        for prop_name, prop_schema in schema_dict.get("properties", {}).items():
            prop_format = prop_schema.get("schema_format", "") or prop_schema.get("format", "")
            prop_type = prop_schema.get("type", "str")
            if is_multipart and prop_format == "binary":
                file_fields.append(_build_upload_file_field_line(prop_name))
                continue
            if not is_multipart and prop_format == "binary":
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
                py_type = _resolve_array_type(prop_schema)
            else:
                py_type = _PYTHON_TYPE_MAP.get(prop_type, "str")
            form_fields.append(_build_form_field_line(prop_name, py_type))

        if is_multipart:
            # multipart 的 Content-Type 故意不自动生成：Playwright 会在发送时
            # 自动加 ``boundary=<...>`` 段，显式 ``multipart/form-data``（无 boundary）
            # 会被 Playwright 原样发送，导致服务端无法解析 multipart body → 400。
            return RequestBodyFields(
                form_fields=form_fields,
                file_fields=file_fields,
                upload_as_multipart=bool(file_fields) or bool(form_fields),
                body_kind=RequestBodyKind.MULTIPART_FORM,
                content_type=None,
            )
        return RequestBodyFields(
            form_fields=form_fields,
            body_kind=RequestBodyKind.URLENCODED_FORM,
            content_type=media_type,
        )

    def _build_raw_body(
        self,
        schema: Any,
        media_type: str,
        endpoint: Endpoint[Any, Any, Any],
    ) -> RequestBodyFields:
        """非 JSON 非 form 的 fallback（text/plain / application/xml 等）。

        与 JSON body 路径共用 schema 形态分流（$ref / inline / primitive），
        区别仅是 content_type 不同。

        :param schema: media_type_schema 节点。
        :param media_type: 媒体类型字符串。
        :param endpoint: 当前 :class:`Endpoint` IR 对象。
        :return: :class:`RequestBodyFields`。
        """
        if schema is None:
            return RequestBodyFields(
                body_kind=RequestBodyKind.RAW,
                content_type=media_type,
            )
        if self._is_reference(schema):
            model_name = _to_pascal_case(schema.ref.rsplit("/", 1)[-1])
            return RequestBodyFields(
                imported_models=[model_name],
                body_kind=RequestBodyKind.RAW,
                content_type=media_type,
            )
        schema_dict = schema.model_dump(mode="json")
        schema_type = schema_dict.get("type", "")
        if schema_type in {"string", "integer", "number", "boolean"}:
            field_name = _to_field_name(endpoint.operation_id)
            py_type = _PYTHON_TYPE_MAP.get(schema_type, "str")
            return RequestBodyFields(
                scalar_body_field=f"{field_name}: Annotated[{py_type}, Body()]",
                body_kind=RequestBodyKind.RAW,
                content_type=media_type,
            )
        model_name = f"{_to_pascal_case(endpoint.operation_id)}Request"
        return RequestBodyFields(
            imported_models=[model_name],
            body_kind=RequestBodyKind.RAW,
            content_type=media_type,
        )

    @staticmethod
    def _build_content_type_header(
        header_fields: list[str],
        content_type: str | None,
    ) -> str | None:
        """当 endpoint 无显式 ``Content-Type`` header 字段时，生成自动派生。

        渲染 ``content_type: Annotated[str, Header(), Field(serialization_alias="Content-Type")] = "<media_type>"``，
        保证运行时发送的 Content-Type 与 spec 一致。
        已有显式 ``Content-Type`` header 字段时返回 ``None``，避免冲突。

        :param header_fields: 已收集的 header 字段声明字符串列表（query/path
            阶段渲染后）。通过字符串搜索 ``alias="Content-Type"`` 判重。
        :param content_type: ``RequestBodyFields.content_type``，为 ``None`` 时
            不需要生成。
        :return: 字段声明字符串，已存在显式 Content-Type 或无 content_type 时返回 ``None``。
        """
        if content_type is None:
            return None
        if any('alias="Content-Type"' in line for line in header_fields):
            return None
        return (
            f'content_type: Annotated[str, Header(), '
            f'Field(serialization_alias="Content-Type")] = "{content_type}"'
        )

    def _extract_response_info(
        self,
        responses: dict[str, Any] | None,
        endpoint: Endpoint[Any, Any, Any],
    ) -> list[str]:
        """提取响应模型名列表（也是要从 ``.models`` 导入的类名集合）。

        遍历 ``responses`` 的所有键（数字状态码与 ``default`` 一视同仁），
        按字典插入顺序处理；没有 ``application/json`` 内容的响应会被跳过。
        命名规则：

        - ``$ref`` 路径：取末段并 PascalCase 化（对齐 ``datamodel-code-generator``
          对 ``components.schemas`` key 的自动 PascalCase 行为，例如
          ``user-profile`` → ``UserProfile``），不消耗 inline 计数器。
        - Inline 对象：按出现顺序使用 ``{PascalOpId}Response``、
          ``{PascalOpId}Response1``、``{PascalOpId}Response2`` 命名（对齐
          ``datamodel-code-generator`` 的 ``use_operation_id_as_name=True``
          —— 该模式下多状态 inline response 按递增后缀区分）。

        返回结果按 ``responses`` 迭代顺序保序，重复项用 ``dict.fromkeys``
        去重（保留首次出现的相对位置）。

        :param responses: OpenAPI 响应字典（状态码 → Response 对象），可为
            ``None`` 或空。
        :param endpoint: 当前 :class:`Endpoint` IR 对象。
        :return: 响应模型名列表，无任何可命名响应时返回空列表。
        """
        if not responses:
            return []

        operation_id_pascal = _to_pascal_case(endpoint.operation_id)
        inline_counter = 0
        ordered_names: list[str] = []

        for response in responses.values():
            content = getattr(response, "content", None) or {}
            json_content = content.get("application/json")
            if not json_content:
                continue
            schema = getattr(json_content, "media_type_schema", None)
            if self._is_reference(schema):
                ordered_names.append(_to_pascal_case(schema.ref.rsplit("/", 1)[-1]))
                continue
            inline_counter += 1
            if inline_counter == 1:
                ordered_names.append(f"{operation_id_pascal}Response")
            else:
                ordered_names.append(f"{operation_id_pascal}Response{inline_counter - 1}")

        return list(dict.fromkeys(ordered_names))


def make_endpoint_renderer(spec_version: SpecVersion) -> EndpointRenderer[Any]:
    """按 spec 版本构造对应的 :class:`EndpointRenderer`。

    工厂在初始化时把版本对应的 Reference 类（``Reference30`` 或
    ``Reference31``）注入到渲染器；之后渲染器内部用
    :meth:`EndpointRenderer._is_reference` 在 ``object`` 上做版本感知
    收窄，避免使用 ``Reference30 | Reference31`` 联合类型。

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


def _map_json_schema_type(json_type: str) -> str:
    """把 JSON Schema 类型映射为 Python 类型。"""
    return {
        "string": "str",
        "integer": "int",
        "number": "float",
        "boolean": "bool",
        "array": "list",
        "object": "dict",
    }.get(json_type, json_type)


# JSON Schema primitive type → Python 类型字符串映射（form / scalar body 共用）。
_PYTHON_TYPE_MAP: dict[str, str] = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
}


def _resolve_array_type(prop_schema: dict[str, Any]) -> str:
    """对 ``type: array`` 的 property 派生 ``list[T]`` 字符串。

    从 ``prop_schema["items"]["type"]`` 取元素类型映射到 Python 类型名；
    ``items`` 不存在或 type 不在 :data:`_PYTHON_TYPE_MAP` 时 fallback 到
    ``"str"``。

    :param prop_schema: property 的 schema 字典（含 ``type`` / ``items``）。
    :return: ``"list[<element>]"`` 形式的 Python 类型字符串。
    """
    items = prop_schema.get("items", {})
    items_type = items.get("type", "") if isinstance(items, dict) else ""
    element_type = _PYTHON_TYPE_MAP.get(items_type, "str")
    return f"list[{element_type}]"


def _build_form_field_line(name: str, py_type: str) -> str:
    """构造 form 字段声明字符串，含非 snake_case 自动 ``Field(serialization_alias=...)``。

    字段名走 :func:`_to_field_name` 处理 hyphen / 关键字 / 数字开头等边界；
    若转换结果与原名不同（非合法 snake_case），追加
    ``Field(serialization_alias=<原名!r>)`` 让 FastAPI Form 提交时用原名，
    避免接口协议破坏（参考 :func:`_build_param_field_line` 的非 snake_case 分支）。

    :param name: 原始 OpenAPI property 名称。
    :param py_type: Python 类型字符串。
    :return: 字段声明字符串。
    """
    field_name = _to_field_name(name)
    if not _is_snake_case(name):
        return f"{field_name}: Annotated[{py_type}, Form(), Field(serialization_alias={name!r})]"
    return f"{field_name}: Annotated[{py_type}, Form()]"


def _build_upload_file_field_line(name: str) -> str:
    """构造 multipart file 字段声明字符串。

    裸 ``UploadFile``，不带 ``Field(serialization_alias=...)``：
    runtime ``UploadFile`` 是 dataclass，序列化由 FastAPI / Playwright
    FormData 直接处理，alias 语义不适用（与 plan "不引入 File() 标记" 一致）。

    字段名同样走 :func:`_to_field_name` 处理边界。

    :param name: 原始 OpenAPI property 名称。
    :return: ``"<name>: UploadFile"`` 字段声明字符串。
    """
    field_name = _to_field_name(name)
    return f"{field_name}: UploadFile"


def _build_param_field_line(
    name: str,
    param_type: str,
    required: bool,
    location: str,
) -> str:
    """构建参数（query / path / header）字段声明字符串。

    使用 FastAPI 推荐的 ``Annotated[...]`` 形式：所有 metadata
    （``Header()`` / ``Field(serialization_alias=...)``）放进
    ``Annotated[...]`` 内，只在可选字段上保留 ``= None`` 默认值。

    八种分支形态：

    - header × required × snake: ``name: Annotated[T, Header()]``
    - header × required × non-snake:
      ``name: Annotated[T, Header(), Field(serialization_alias='X')]``
    - header × optional × snake:
      ``name: Annotated[T | None, Header()] = None``
    - header × optional × non-snake:
      ``name: Annotated[T | None, Header(), Field(serialization_alias='X')] = None``
    - query/path × required × snake: ``name: T``
    - query/path × required × non-snake:
      ``name: Annotated[T, Field(serialization_alias='X')]``
    - query/path × optional × snake: ``name: T | None = None``
    - query/path × optional × non-snake:
      ``name: Annotated[T | None, Field(serialization_alias='X')] = None``

    :param name: 原始 OpenAPI 参数名。
    :param param_type: Python 类型字符串。
    :param required: 是否必需。
    :param location: ``"header"`` / ``"query"`` / ``"path"``。
    :return: 字段声明字符串。
    """
    is_header = location == "header"
    is_snake = _is_snake_case(name)
    field_name = name if is_snake else _to_field_name(name)

    base_type = param_type if required else f"{param_type} | None"

    metadata: list[str] = []
    if is_header:
        metadata.append("Header()")
    if not is_snake:
        metadata.append(f"Field(serialization_alias={name!r})")

    if metadata:
        annotation = f"Annotated[{base_type}, {', '.join(metadata)}]"
    else:
        annotation = base_type

    default = "" if required else " = None"
    return f"{field_name}: {annotation}{default}"


def render_to_file(
    output_dir: str | Path,
    file_name: str,
    rendered_code: str,
) -> Path:
    """将渲染后的代码写入文件。

    ``file_name`` 由 ``EndpointRenderer.render()`` 一并返回（从
    ``operation_id`` 派生），本函数只负责落盘。

    :param output_dir: 输出目录。
    :param file_name: 目标文件名（含 ``.py`` 后缀）。
    :param rendered_code: 渲染后的 Python 代码。
    :return: 写入的文件路径。
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    file_path = output_path / file_name
    file_path.write_text(rendered_code, encoding="utf-8")
    return file_path
