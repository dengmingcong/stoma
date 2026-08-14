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

请求体渲染管道
==============

请求体在 parser 阶段（:func:`src.openapi.model_generator._expand_path_refs`）
已经通过 jsonref 把 ``$ref`` 一次性展开，展开结果存到
``endpoint.expanded_raw_request_body``（dict 形态）。renderer 通过
:meth:`_extract_request_body_info` 7 步流程判断 body 形态，并构造
:class:`BaseRequestBodyFields` 子类实例。NONE 路径返回 ``None``，由
:meth:`render` 用 ``isinstance`` 拍平为模板变量。
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any, Protocol, TypeGuard

from jinja2 import Environment, FileSystemLoader, Template
from pydantic.alias_generators import to_snake

from src.openapi._naming import _is_snake_case, _to_field_name, _to_pascal_case
from src.openapi.models import (
    BaseRequestBodyFields,
    BinaryRequestBodyFields,
    Endpoint,
    JSONRequestBodyFields,
    MultipartFormRequestBodyFields,
    ScalarRequestBodyFields,
    UrlencodedFormRequestBodyFields,
)
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
        body_fields_template = self._extract_request_body_info(
            endpoint.request_body, endpoint
        )
        header_fields, param_fields, uses_field_import = self._extract_params(endpoint.parameters)

        # 响应在前、请求体在后（保持 spec 顺序）；``dict.fromkeys`` 保序去重，避免重名重复 import。
        # model 名字来自 JSON body 路径（import_model），response 路径也独立收集。
        body_import_model = self._body_import_model(body_fields_template)
        models_for_import: list[str] = list(response_type)
        if body_import_model:
            models_for_import.append(body_import_model)
        imported_models = list(dict.fromkeys(models_for_import))

        # 把 BaseRequestBodyFields 子类拍平为 template 变量。
        # NONE 路径返回 None 时模板所有 body 块跳过。
        body_template_vars = self._flatten_body_fields(body_fields_template)

        # 当 _extract_request_body_info 自动派生 Content-Type（body_template_vars.content_type）且
        # 用户未显式声明同名 header field 时，注入一个 Annotated[str, Header()] 字段占位，
        # 避免与运行时派生的 Content-Type 冲突。
        content_type_header = self._build_content_type_header(
            header_fields, body_template_vars["content_type"]
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
            **body_template_vars,
            header_fields=header_fields,
            param_fields=param_fields,
            imported_models=imported_models,
            uses_field_import=uses_field_import,
        )
        return file_name, rendered_code

    @staticmethod
    def _body_import_model(
        body_fields: BaseRequestBodyFields | None,
    ) -> str | None:
        """从 body_fields 抽取 import_model 字符串（仅 JSON 路径填充）。

        非 JSON 子类（urlencoded / multipart / binary / scalar）无
        ``import_model`` 概念，返回 ``None`` 让 template 跳过 import。

        :param body_fields: body 渲染字段（NONE 路径为 None）。
        :return: model 名（PascalCase）或 ``None``。
        """
        if isinstance(body_fields, JSONRequestBodyFields):
            return body_fields.import_model
        return None

    @staticmethod
    def _flatten_body_fields(
        body_fields: BaseRequestBodyFields | None,
    ) -> dict[str, Any]:
        """把 BaseRequestBodyFields 子类拍平为 template 变量字典。

        NONE 路径返回空字典（所有 body 块条件不成立，自动跳过）。

        :param body_fields: body 渲染字段（NONE 路径为 None）。
        :return: 模板可直接 ``**vars`` 展开的字典（key 名对齐
            ``endpoint.py.jinja2`` 的变量名）。
        """
        if body_fields is None:
            return {
                "import_model": None,
                "scalar_field": None,
                "form_text_fields": [],
                "form_file_fields": [],
                "binary_file_field": None,
                "upload_as_multipart": True,
                "content_type": None,
            }
        if isinstance(body_fields, JSONRequestBodyFields):
            return {
                "import_model": body_fields.import_model,
                "scalar_field": None,
                "form_text_fields": [],
                "form_file_fields": [],
                "binary_file_field": None,
                "upload_as_multipart": True,
                "content_type": body_fields.content_type,
            }
        if isinstance(body_fields, UrlencodedFormRequestBodyFields):
            return {
                "import_model": None,
                "scalar_field": None,
                "form_text_fields": body_fields.form_text_fields,
                "form_file_fields": [],
                "binary_file_field": None,
                "upload_as_multipart": True,
                "content_type": body_fields.content_type,
            }
        if isinstance(body_fields, MultipartFormRequestBodyFields):
            return {
                "import_model": None,
                "scalar_field": None,
                "form_text_fields": body_fields.form_text_fields,
                "form_file_fields": body_fields.form_file_fields,
                "binary_file_field": None,
                "upload_as_multipart": True,
                "content_type": body_fields.content_type,
            }
        if isinstance(body_fields, BinaryRequestBodyFields):
            return {
                "import_model": None,
                "scalar_field": None,
                "form_text_fields": [],
                "form_file_fields": [],
                "binary_file_field": body_fields.binary_file_field,
                "upload_as_multipart": False,
                "content_type": body_fields.content_type,
            }
        if isinstance(body_fields, ScalarRequestBodyFields):
            return {
                "import_model": None,
                "scalar_field": body_fields.scalar_field,
                "form_text_fields": [],
                "form_file_fields": [],
                "binary_file_field": None,
                "upload_as_multipart": True,
                "content_type": body_fields.content_type,
            }
        msg = f"Unsupported body_fields type: {type(body_fields).__name__}"
        raise TypeError(msg)

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
            # 上游通过 ``_expand_path_refs`` 展开为内联 schema，因此
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
    ) -> BaseRequestBodyFields | None:
        """按 spec 的 media type 分类请求体，返回对应 :class:`BaseRequestBodyFields` 子类实例。

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

        JSON 路径的 schema 形态通过 ``endpoint.request_body.content["application/json"].
        media_type_schema`` 原 openapi-pydantic 实例判断；非 JSON 路径的 schema
        从 ``endpoint.expanded_raw_request_body`` 读 dict 形态（parser 上游
        :func:`src.openapi.model_generator._expand_path_refs` 已展开）。

        :param request_body: :class:`RequestBody` 对象（来自 openapi-pydantic）。
        :param endpoint: 当前 :class:`Endpoint` IR 对象。
        :return: :class:`BaseRequestBodyFields` 子类实例；NONE 路径返回 ``None``。
        :raise OpenAPISchemaError: 多 media type、schema 含 oneOf/anyOf/allOf key、
            或 schema 形态不支持。
        """
        if request_body is None:
            return None

        content = getattr(request_body, "content", None)
        if not isinstance(content, dict) or not content:
            return None

        if len(content) != 1:
            msg = f"Multiple media types in requestBody not supported: {list(content.keys())}"
            raise OpenAPISchemaError(msg)

        media_type, media_type_obj = next(iter(content.items()))
        schema = getattr(media_type_obj, "media_type_schema", None)

        # 步骤 3：application/json
        if media_type == "application/json":
            return self._build_json_body(schema, endpoint)

        # 步骤 4：multipart/form-data
        if media_type == "multipart/form-data":
            schema_dict = _get_expanded_schema_dict(endpoint, media_type)
            _reject_oneof_anyof_allof(schema_dict, media_type)
            return self._build_multipart_body(schema_dict, media_type)

        # 步骤 5：application/x-www-form-urlencoded
        if media_type == "application/x-www-form-urlencoded":
            schema_dict = _get_expanded_schema_dict(endpoint, media_type)
            _reject_oneof_anyof_allof(schema_dict, media_type)
            return self._build_urlencoded_body(schema_dict, media_type)

        # 步骤 6：string + format=binary（不限 media type）
        if schema is not None:
            schema_dict = schema.model_dump(mode="json")
            if schema_dict.get("type") == "string" and (
                schema_dict.get("schema_format", "") or schema_dict.get("format", "")
            ) == "binary":
                return self._build_binary_body(schema_dict, media_type, endpoint)

        # 步骤 7：兜底 RAW
        schema_dict = _get_expanded_schema_dict(endpoint, media_type)
        return self._build_scalar_body(schema_dict, media_type, endpoint)

    def _build_json_body(
        self,
        schema: Any,
        endpoint: Endpoint[Any, Any, Any],
    ) -> JSONRequestBodyFields | ScalarRequestBodyFields:
        """构造 ``application/json`` 请求体渲染信息。

        schema 形态分流：

        - ``$ref`` 指向 ``components.schemas.*`` → 取末段 PascalCase 化为 model 名，
          返回 :class:`JSONRequestBodyFields`。
        - 内联 object schema（dmcg 已生成对应 ``<OpId>Request`` 模型）→ 引用之，
          返回 :class:`JSONRequestBodyFields`。
        - primitive schema → 返回 :class:`ScalarRequestBodyFields`，字段名按
          :func:`_to_field_name` 从 operationId 派生（snake_case 化）。

        :param schema: ``application/json`` 的 media_type_schema 节点
            （openapi-pydantic ``Schema`` 实例，可能为 ``None``）。
        :param endpoint: 当前 :class:`Endpoint` IR 对象。
        :return: :class:`JSONRequestBodyFields` 或 :class:`ScalarRequestBodyFields`。
        """
        if schema is None:
            return JSONRequestBodyFields(content_type="application/json")

        if self._is_reference(schema):
            ref_path = schema.ref.rsplit("/", 1)[-1]
            model_name = _to_pascal_case(ref_path)
            return JSONRequestBodyFields(
                import_model=model_name,
                content_type="application/json",
            )

        schema_type = getattr(schema, "type", None)
        if schema_type in {"string", "integer", "number", "boolean"}:
            field_name = _to_field_name(endpoint.operation_id)
            py_type = _PYTHON_TYPE_MAP.get(schema_type, "str")
            return ScalarRequestBodyFields(
                scalar_field=f"{field_name}: Annotated[{py_type}, Body()]",
                content_type="application/json",
            )

        # inline object schema → dmcg 已生成 ``<OpId>Request`` 模型。
        model_name = f"{_to_pascal_case(endpoint.operation_id)}Request"
        return JSONRequestBodyFields(
            import_model=model_name,
            content_type="application/json",
        )

    @staticmethod
    def _build_scalar_body(
        schema_dict: dict[str, Any],
        media_type: str,
        endpoint: Endpoint[Any, Any, Any],
    ) -> ScalarRequestBodyFields:
        """兜底 RAW 路径：primitive schema → 单字段 body。

        非 JSON / 非 form / 非 binary 的 media type（``text/plain`` /
        ``application/xml`` 等）且 schema 是 primitive type 时返回
        :class:`ScalarRequestBodyFields`。

        :param schema_dict: 展开后的 schema 字典（来自
            ``endpoint.expanded_raw_request_body``，可能为空 dict）。
        :param media_type: 媒体类型字符串。
        :param endpoint: 当前 :class:`Endpoint` IR 对象。
        :return: :class:`ScalarRequestBodyFields`。
        :raise OpenAPISchemaError: schema 不是 primitive type（不支持）。
        """
        schema_type = schema_dict.get("type", "")
        if schema_type not in {"string", "integer", "number", "boolean"}:
            msg = (
                f"Unsupported RAW body schema type for {endpoint.operation_id!r}: {schema_type!r}. "
                "Only primitive types (string/integer/number/boolean) are supported in non-JSON media types."
            )
            raise OpenAPISchemaError(msg)
        field_name = _to_field_name(endpoint.operation_id)
        py_type = _PYTHON_TYPE_MAP.get(schema_type, "str")
        return ScalarRequestBodyFields(
            scalar_field=f"{field_name}: Annotated[{py_type}, Body()]",
            content_type=media_type,
        )

    def _build_urlencoded_body(
        self,
        schema_dict: dict[str, Any],
        media_type: str,
    ) -> UrlencodedFormRequestBodyFields:
        """构造 ``application/x-www-form-urlencoded`` 请求体渲染信息。

        遍历 ``properties``：

        - ``format == "binary"`` 时 ``warnings.warn(...)``（FastAPI Form 字段
          不接受 binary 内容），仍按普通 Form 字段渲染；
        - 其他 primitive 走 ``Annotated[T, Form()]``；
        - array 走 :func:`_resolve_array_type` 派生 ``list[T]``；
        - 非 snake_case 字段名自动追加 ``Field(serialization_alias=...)``
          保留原名（:func:`_build_form_field_line` 已处理）。

        :param schema_dict: 展开后的 schema 字典（来自
            ``endpoint.expanded_raw_request_body``）。
        :param media_type: 媒体类型字符串。
        :return: :class:`UrlencodedFormRequestBodyFields`。
        """
        form_text_fields: list[str] = []
        for prop_name, prop_schema in schema_dict.get("properties", {}).items():
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
                py_type = _resolve_array_type(prop_schema)
            else:
                py_type = _PYTHON_TYPE_MAP.get(prop_type, "str")
            form_text_fields.append(_build_form_field_line(prop_name, py_type))

        return UrlencodedFormRequestBodyFields(
            form_text_fields=form_text_fields,
            content_type=media_type,
        )

    def _build_multipart_body(
        self,
        schema_dict: dict[str, Any],
        media_type: str,
    ) -> MultipartFormRequestBodyFields:
        """构造 ``multipart/form-data`` 请求体渲染信息。

        遍历 ``properties``：

        - ``format == "binary"`` → ``<name>: UploadFile`` 进入 ``form_file_fields``；
        - 其他 primitive → ``<name>: Annotated[T, Form()]`` 进入 ``form_text_fields``。

        Content-Type 故意不自动派生（Playwright 自动加 boundary 段，
        显式 ``multipart/form-data`` 无 boundary 会导致服务端 400）。

        :param schema_dict: 展开后的 schema 字典（来自
            ``endpoint.expanded_raw_request_body``）。
        :param media_type: 媒体类型字符串。
        :return: :class:`MultipartFormRequestBodyFields`，``content_type=None``。
        """
        form_text_fields: list[str] = []
        form_file_fields: list[str] = []
        for prop_name, prop_schema in schema_dict.get("properties", {}).items():
            if not isinstance(prop_schema, dict):
                continue
            prop_format = prop_schema.get("schema_format", "") or prop_schema.get("format", "")
            prop_type = prop_schema.get("type", "str")
            if prop_format == "binary":
                form_file_fields.append(_build_upload_file_field_line(prop_name))
                continue
            if prop_type == "array":
                py_type = _resolve_array_type(prop_schema)
            else:
                py_type = _PYTHON_TYPE_MAP.get(prop_type, "str")
            form_text_fields.append(_build_form_field_line(prop_name, py_type))

        return MultipartFormRequestBodyFields(
            form_text_fields=form_text_fields,
            form_file_fields=form_file_fields,
            content_type=None,
        )

    def _build_binary_body(
        self,
        schema_dict: dict[str, Any],
        media_type: str,
        endpoint: Endpoint[Any, Any, Any],
    ) -> BinaryRequestBodyFields:
        """构造 binary 单文件 raw body 渲染信息。

        ``string + format=binary`` 的 schema 派生单一 ``<name>: UploadFile``
        字段，字段名按 :func:`_to_field_name` 从 operationId 派生。
        对应 ``upload_as_multipart=False``（由 :class:`BinaryRequestBodyFields`
        类型本身表达，:meth:`_flatten_body_fields` 拍平时固定为 ``False``）。

        :param schema_dict: 展开后的 schema 字典。
        :param media_type: 媒体类型字符串（用于 Content-Type header 派生）。
        :param endpoint: 当前 :class:`Endpoint` IR 对象。
        :return: :class:`BinaryRequestBodyFields`。
        """
        field_name = _to_field_name(endpoint.operation_id)
        return BinaryRequestBodyFields(
            binary_file_field=f"{field_name}: UploadFile",
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


def _reject_oneof_anyof_allof(schema_dict: dict[str, Any], media_type: str) -> None:
    """非 JSON 表单路径检测顶层 ``oneOf`` / ``anyOf`` / ``allOf`` key。

    multipart / urlencoded form 路径不支持复合 schema（顶层是复合 key 时
    renderer 无法静态推断 fields），命中即抛 :class:`OpenAPISchemaError`。
    JSON 路径不受影响（oneOf/anyOf/allOf 通过 ``$ref`` 解析走 dmcg 合并路径）。

    :param schema_dict: 展开后的 schema 字典。
    :param media_type: 媒体类型字符串（用于错误信息）。
    :raise OpenAPISchemaError: schema 含顶层 oneOf/anyOf/allOf key。
    """
    for composite_key in ("oneOf", "anyOf", "allOf"):
        if composite_key in schema_dict:
            msg = (
                f"{media_type} schema with top-level {composite_key!r} is not supported; "
                "use application/json with $ref + inline merge instead."
            )
            raise OpenAPISchemaError(msg)


def _get_expanded_schema_dict(
    endpoint: Endpoint[Any, Any, Any],
    media_type: str,
) -> dict[str, Any]:
    """从 ``endpoint.expanded_raw_request_body`` 取指定 ``media_type`` 的 schema 字典。

    ``expanded_raw_request_body`` 是 parser 上游通过
    :func:`src.openapi.model_generator._expand_path_refs` 展开后的 requestBody dict，
    结构为 ``{"content": {"<media_type>": {"schema": {…}}}}``。

    :param endpoint: 当前 :class:`Endpoint` IR 对象。
    :param media_type: 目标 media type。
    :return: schema 字典，缺失或非 dict 时返回空 dict（兜底）。
    """
    expanded = endpoint.expanded_raw_request_body
    if not isinstance(expanded, dict):
        return {}
    content = expanded.get("content", {})
    if not isinstance(content, dict):
        return {}
    media_type_obj = content.get(media_type, {})
    if not isinstance(media_type_obj, dict):
        return {}
    schema = media_type_obj.get("schema", {})
    if not isinstance(schema, dict):
        return {}
    return schema


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