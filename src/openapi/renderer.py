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

:meth:`_extract_request_body_info` 7 步流程判断 body 形态，并构造
:class:`BinaryRequestBodyFields` / :class:`ScalarRequestBodyFields` /
:class:`JSONRequestBodyFields` / :class:`UrlencodedFormRequestBodyFields` /
:class:`MultipartFormRequestBodyFields` 子类实例。NONE 路径返回 ``None``，由
:meth:`render` 用 ``isinstance`` 拍平为模板变量。

两条路径读取 schema：

- JSON 路径调用 :meth:`EndpointRenderer._get_media_type_schema` 从
  ``request_body.content`` 拿原始 Pydantic 模型（Reference30/31 或 Schema30/31），
  由 :meth:`_build_json_body` 直接用 :meth:`_is_reference` 派生 model 名。
- 非 JSON 路径（multipart / urlencoded / binary / RAW scalar）调用
  :meth:`EndpointRenderer._get_expanded_schema_dict` 走 jsonref 展开
  （仅展开 ``$ref``，不影响 model_generator 已生成的 import——dmcg 阶段已完成），
  用于遍历 ``properties``。
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any, Protocol, TypeGuard

import jsonref
from jinja2 import Environment, FileSystemLoader, Template
from pydantic import BaseModel
from pydantic.alias_generators import to_snake

from src.openapi._naming import _is_snake_case, _to_field_name, _to_pascal_case
from src.openapi.models import (
    BinaryRequestBodyFields,
    Endpoint,
    JSONRequestBodyFields,
    MultipartFormRequestBodyFields,
    RequestBodyFields,
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
        body_fields_template = self._extract_request_body_info(endpoint.request_body, endpoint)
        header_fields, param_fields, uses_field_import = self._extract_params(endpoint.parameters)

        # 响应在前、请求体在后（保持 spec 顺序）；``dict.fromkeys`` 保序去重，避免重名重复 import。
        # model 名字来自 JSON body 路径（import_model），response 路径也独立收集。
        body_import_model = self._body_import_model(body_fields_template)
        models_for_import: list[str] = list(response_type)
        if body_import_model:
            models_for_import.append(body_import_model)
        imported_models = list(dict.fromkeys(models_for_import))

        # 把 body fields 子类拍平为 template 变量。
        # NONE 路径返回 None 时模板所有 body 块跳过。
        body_template_vars = self._flatten_body_fields(body_fields_template)

        # 仅 binary body 需要 renderer 派生 Content-Type header field
        # （Playwright 无法从裸字节推断）。scalar body 通过 ``Body(media_type=...)``
        # 路径传递 Content-Type，由 client 通过 ``param_info.media_type`` 派生。
        # 其他类型 Content-Type 由 Playwright 根据 body 形态自动设置，renderer 不干预；
        # 用户在 APIRoute 中显式提供的 Content-Type header field 仍由
        # :meth:`_serialize_header_params` 透传给 Playwright。
        content_type_header = self._build_content_type_header(header_fields, body_template_vars["media_type"])
        if content_type_header is not None:
            header_fields.append(content_type_header)
            uses_field_import = uses_field_import or not _is_snake_case("Content-Type")

        # body 字段（非 snake_case 时含 ``Field(serialization_alias=)``）也会触发 Field import。
        # 检查 4 类 body 字段字符串中是否含 ``Field(``，避免 multipart 纯文件场景漏 import。
        uses_field_import = uses_field_import or self._body_fields_use_field(body_template_vars)

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
        body_fields: RequestBodyFields | None,
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
        body_fields: RequestBodyFields | None,
    ) -> dict[str, Any]:
        """把 body fields 子类拍平为 template 变量字典。

        NONE 路径返回空字典（所有 body 块条件不成立，自动跳过）。

        ``media_type`` 字段仅在 binary / scalar 子类有值，供 :meth:`render`
        调用 :meth:`_build_content_type_header` 派生 Content-Type header；
        JSON / urlencoded / multipart 均为 ``None``，Playwright 自动处理 Content-Type。

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
                "media_type": None,
            }
        if isinstance(body_fields, JSONRequestBodyFields):
            return {
                "import_model": body_fields.import_model,
                "scalar_field": None,
                "form_text_fields": [],
                "form_file_fields": [],
                "binary_file_field": None,
                "upload_as_multipart": True,
                "media_type": None,
            }
        if isinstance(body_fields, UrlencodedFormRequestBodyFields):
            return {
                "import_model": None,
                "scalar_field": None,
                "form_text_fields": body_fields.form_text_fields,
                "form_file_fields": [],
                "binary_file_field": None,
                "upload_as_multipart": True,
                "media_type": None,
            }
        if isinstance(body_fields, MultipartFormRequestBodyFields):
            return {
                "import_model": None,
                "scalar_field": None,
                "form_text_fields": body_fields.form_text_fields,
                "form_file_fields": body_fields.form_file_fields,
                "binary_file_field": None,
                "upload_as_multipart": True,
                "media_type": None,
            }
        if isinstance(body_fields, BinaryRequestBodyFields):
            return {
                "import_model": None,
                "scalar_field": None,
                "form_text_fields": [],
                "form_file_fields": [],
                "binary_file_field": body_fields.binary_file_field,
                "upload_as_multipart": False,
                "media_type": body_fields.media_type,
            }
        if isinstance(body_fields, ScalarRequestBodyFields):
            return {
                "import_model": None,
                "scalar_field": body_fields.scalar_field,
                "form_text_fields": [],
                "form_file_fields": [],
                "binary_file_field": None,
                "upload_as_multipart": True,
                "media_type": None,
            }
        msg = f"Unsupported body_fields type: {type(body_fields).__name__}"
        raise TypeError(msg)

    @staticmethod
    def _body_fields_use_field(body_template_vars: dict[str, Any]) -> bool:
        """判断 body 字段声明中是否含 ``Field(``，决定是否追加 ``from pydantic import Field``。

        4 类 body 字段（``form_text_fields`` / ``form_file_fields`` /
        ``binary_file_field`` / ``scalar_field``）的非 snake_case 形式都会
        包含 ``Field(serialization_alias=...)``。template 只看
        ``uses_field_import`` 决定是否加 import，所以 body-only Field 用法
        需要在 render 阶段显式翻起该标志。

        :param body_template_vars: :meth:`_flatten_body_fields` 输出的字典。
        :return: 任意 body 字段含 ``Field(`` 子串时返回 ``True``。
        """
        for key in ("form_text_fields", "form_file_fields"):
            for line in body_template_vars.get(key, []):
                if "Field(" in line:
                    return True
        for key in ("binary_file_field", "scalar_field"):
            value = body_template_vars.get(key)
            if isinstance(value, str) and "Field(" in value:
                return True
        return False

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

        JSON 路径调用 :func:`_get_expanded_schema_dict` 从 ``request_body.content``
        拿原始 media_type_schema 并走 jsonref 展开（仅展开 ``$ref``，不影响
        model_generator 已生成的 import——dmcg 阶段已完成）。

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
            msg = f"Multiple media types in requestBody not supported: {list(content.keys())}"
            raise OpenAPISchemaError(msg)

        media_type, _ = next(iter(content.items()))
        expanded_schema_dict: dict[str, Any] | None = self._get_expanded_schema_dict(request_body, media_type)

        # 步骤 3：application/json（dmcg 处理顶层 oneOf/anyOf/allOf，无需组合子检查）
        if media_type == "application/json":
            if self._is_primitive_schema_dict(expanded_schema_dict):
                return self._build_scalar_body(expanded_schema_dict, media_type)
            schema_model = self._get_media_type_schema(request_body, media_type)
            return self._build_json_body(endpoint, schema_model)

        # 非 JSON 路径统一调用一次组合子检查，覆盖 multipart / urlencoded / binary / 兜底 RAW。
        # 顶层 oneOf/anyOf/allOf 在非 JSON media type 下 renderer 无法静态推断 fields。
        if self._has_combinator(expanded_schema_dict):
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
        if self._is_binary_schema_dict(expanded_schema_dict):
            return self._build_binary_body(media_type)

        # 步骤 7：兜底 RAW
        return self._build_scalar_body(expanded_schema_dict, media_type)

    @staticmethod
    def _has_combinator(schema: dict[str, Any] | None) -> bool:
        """检查 schema 是否含非空顶层 ``oneOf`` / ``anyOf`` / ``allOf`` key。
        multipart / urlencoded form 不支持顶层复合 key（renderer 无法静态推断
        fields）；JSON 路径也已显式拒绝（dmcg 处理 inline union 时需要
        ``$ref`` + inline merge 配合，原始 inline union 不再支持）。

        openapi-pydantic v3 的 ``Schema.model_dump(mode="json")`` 会把未设置的
        ``oneOf`` / ``anyOf`` / ``allOf`` 输出为显式 ``None`` key，因此判重时
        必须同时检查值非 ``None``。

        :param schema: 展开后的 schema 字典（可能为 ``None``）。
        :return: 命中任一非空复合 key 时返回 ``True``。
        """
        if not isinstance(schema, dict):
            return False
        return any(schema.get(key) is not None for key in ("oneOf", "anyOf", "allOf"))

    @staticmethod
    def _is_primitive_schema_dict(schema: dict[str, Any] | None) -> bool:
        """判断 schema 是否为 primitive（string / integer / number / boolean）。

        :param schema: 展开后的 schema 字典（可能为 ``None``）。
        :return: ``type`` 字段命中 primitive 类型集合时返回 ``True``。
        """
        if not isinstance(schema, dict):
            return False
        return schema.get("type") in {"string", "integer", "number", "boolean"}

    @staticmethod
    def _is_binary_schema_dict(schema: dict[str, Any] | None) -> bool:
        """判断 schema 是否为 ``string + format=binary``（binary raw body）。

        兼容 openapi-pydantic v3 的 ``schema_format`` 双 key 兜底。

        :param schema: 展开后的 schema 字典（可能为 ``None``）。
        :return: ``type == "string"`` 且 ``format == "binary"`` 时返回 ``True``。
        """
        if not isinstance(schema, dict):
            return False
        if schema.get("type") != "string":
            return False
        return (schema.get("schema_format", "") or schema.get("format", "")) == "binary"

    @staticmethod
    def _get_media_type_schema(
        request_body: Any,
        media_type: str,
    ) -> BaseModel | None:
        """从 ``request_body.content`` 取指定 ``media_type`` 的原始 schema Pydantic 模型。

        与 :meth:`_get_expanded_schema_dict` 的区别：本方法返回原始 Pydantic 模型
        （``Reference30`` / ``Reference31`` / ``Schema30`` / ``Schema31``），供
        :meth:`_build_json_body` 直接用 :meth:`_is_reference` 检测 Reference 并
        访问 ``schema.ref`` 派生 model 名——jsonref 展开后会丢失 ``$ref`` 信息，
        必须回到原始模型才能拿到。

        非 JSON 路径仍走 :meth:`_get_expanded_schema_dict`（需要遍历 properties）。

        :param request_body: openapi-pydantic ``RequestBody`` 实例。
        :param media_type: 媒体类型字符串（如 ``"application/json"``）。
        :return: 原始 ``media_type_schema`` Pydantic 模型，缺失时返回 ``None``。
        """
        content = getattr(request_body, "content", None)
        if not isinstance(content, dict):
            return None
        media_type_obj = content.get(media_type)
        if media_type_obj is None:
            return None
        return getattr(media_type_obj, "media_type_schema", None)

    @staticmethod
    def _get_expanded_schema_dict(
        request_body: Any,
        media_type: str,
    ) -> dict[str, Any] | None:
        """从 ``request_body.content`` 取指定 ``media_type`` 的 schema 并用 jsonref 展开。

        仅展开 ``$ref``，不影响 model_generator 生成的 import（dmcg 阶段已完成）。

        非 JSON 路径（multipart / urlencoded / binary / RAW scalar）使用本方法
        拿到展开后的 dict 以遍历 ``properties``。JSON 路径使用
        :meth:`_get_media_type_schema` 直接拿原始 Pydantic 模型，
        通过 :meth:`_is_reference` 检测 Reference 并访问 ``schema.ref``。

        对于 openapi-pydantic 的 ``Reference`` 实例（``$ref`` schema），保留
        ``{"$ref": "..."}`` 形式返回——后续若再次引用，可继续从 dict 提取 ref。
        走 jsonref 反而会把 ``$ref`` 替换为 inline 内容，丢失 model 名信息。

        :param request_body: openapi-pydantic ``RequestBody`` 实例。
        :param media_type: 媒体类型字符串（如 ``"application/json"``）。
        :return: 展开后的 schema dict，缺失时返回 ``None``。
        """
        content = getattr(request_body, "content", None)
        if not isinstance(content, dict):
            return None
        media_type_obj = content.get(media_type)
        if media_type_obj is None:
            return None
        media_type_schema = getattr(media_type_obj, "media_type_schema", None)
        if media_type_schema is None:
            return None
        ref_value = getattr(media_type_schema, "ref", None)
        if isinstance(ref_value, str):
            return {"$ref": ref_value}
        schema_dict = media_type_schema.model_dump(mode="json")
        try:
            return jsonref.replace_refs(schema_dict, proxies=False, lazy_load=False)
        except Exception:
            return schema_dict

    def _build_json_body(
        self,
        endpoint: Endpoint[Any, Any, Any],
        schema_model: BaseModel | None,
    ) -> JSONRequestBodyFields:
        """根据 ``schema_model`` 派生 ``import_model``。

        ``schema_model`` 是 :meth:`_get_media_type_schema` 返回的原始 Pydantic
        模型（``Reference30`` / ``Reference31`` / ``Schema30`` / ``Schema31``）。
        用原始模型而不是 jsonref 展开后的 dict 是因为 jsonref 会把 ``$ref`` 替换为
        inline 内容，丢失 model 名信息。

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

        if self._is_reference(schema_model):
            ref_path = str(schema_model.ref).rsplit("/", 1)[-1]
            return JSONRequestBodyFields(import_model=_to_pascal_case(ref_path))

        # inline object schema → dmcg 已生成 ``<OpId>Request`` 模型。
        model_name = f"{_to_pascal_case(endpoint.operation_id)}Request"
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
        - array 走 :func:`_resolve_array_type` 派生 ``list[T]``；
        - 非 snake_case 字段名自动追加 ``Field(serialization_alias=...)``
          保留原名（:func:`_build_form_field_line` 已处理）。

        :param expanded_schema_dict: jsonref 展开后的 schema 字典，可能为 ``None``。
        :return: :class:`UrlencodedFormRequestBodyFields`。
        """
        form_text_fields: list[str] = []
        if expanded_schema_dict is None:
            return UrlencodedFormRequestBodyFields(form_text_fields=form_text_fields)
        for prop_name, prop_schema in expanded_schema_dict.get("properties", {}).items():
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

        return UrlencodedFormRequestBodyFields(form_text_fields=form_text_fields)

    def _build_multipart_body(
        self,
        expanded_schema_dict: dict[str, Any] | None,
    ) -> MultipartFormRequestBodyFields:
        """构造 ``multipart/form-data`` 请求体渲染信息。

        遍历 ``properties``：

        - ``format == "binary"`` → ``<name>: UploadFile`` 进入 ``form_file_fields``；
        - 其他 primitive → ``<name>: Annotated[T, Form()]`` 进入 ``form_text_fields``。

        :param expanded_schema_dict: jsonref 展开后的 schema 字典，可能为 ``None``。
        :return: :class:`MultipartFormRequestBodyFields`（无 content_type，Playwright 自动设置）。
        """
        form_text_fields: list[str] = []
        form_file_fields: list[str] = []
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
        )

    @staticmethod
    def _build_binary_body(
        media_type: str,
    ) -> BinaryRequestBodyFields:
        """构造 binary 单文件 raw body 渲染信息。

        ``string + format=binary`` 的 schema 派生单一 ``body: UploadFile`` 字段。
        字段名固定为 ``body``（避免按 operationId 派生导致非 snake_case 时需要
        ``Field(serialization_alias=...)`` 副作用）。对应 ``upload_as_multipart=False``
        （由 :class:`BinaryRequestBodyFields` 类型本身表达，:meth:`_flatten_body_fields`
        拍平时固定为 ``False``）。

        :param media_type: 媒体类型字符串（用于 Content-Type header 派生）。
        :return: :class:`BinaryRequestBodyFields`。
        """
        return BinaryRequestBodyFields(
            binary_file_field="body: UploadFile",
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

        :param expanded_schema_dict: 展开后的 schema 字典，可能为 ``None``。
        :param media_type: 媒体类型字符串，嵌入 ``Body(media_type=...)``。
        :return: :class:`ScalarRequestBodyFields`。
        :raise OpenAPISchemaError: schema 不是 primitive 类型（兜底 RAW 场景下）。
        """
        if expanded_schema_dict is None:
            return ScalarRequestBodyFields()
        schema_type = expanded_schema_dict.get("type", "str")
        if schema_type not in {"string", "integer", "number", "boolean"}:
            msg = (
                f"Unsupported RAW body schema type: {schema_type!r}. "
                "Only primitive types (string/integer/number/boolean) are supported in non-JSON media types."
            )
            raise OpenAPISchemaError(msg)
        py_type = _PYTHON_TYPE_MAP.get(schema_type, "str")
        scalar_field = f"body: Annotated[{py_type}, Body(media_type={media_type!r})]"
        return ScalarRequestBodyFields(scalar_field=scalar_field)

    @staticmethod
    def _build_content_type_header(
        header_fields: list[str],
        media_type: str | None,
    ) -> str | None:
        """当 endpoint 无显式 ``Content-Type`` header 字段且 ``media_type`` 非空时，生成自动派生。

        渲染 ``content_type: Annotated[str, Header(), Field(serialization_alias="Content-Type")] = "<media_type>"``，
        保证运行时发送的 Content-Type 与 spec 一致。
        已有显式 ``Content-Type`` header 字段时返回 ``None``，避免冲突。

        :param header_fields: 已收集的 header 字段声明字符串列表（query/path
            阶段渲染后）。通过字符串搜索 ``alias="Content-Type"`` 判重。
        :param media_type: body fields 子类的 ``media_type``，为 ``None`` 时
            不需要生成（JSON / urlencoded / multipart 由 Playwright 处理）。
        :return: 字段声明字符串，已存在显式 Content-Type 或 ``media_type`` 为空时返回 ``None``。
        """
        if media_type is None:
            return None
        if any('alias="Content-Type"' in line for line in header_fields):
            return None
        return f'content_type: Annotated[str, Header(), Field(serialization_alias="Content-Type")] = "{media_type}"'

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

    ``name`` 非 snake_case 时追加 ``Field(serialization_alias=<origin>)``
    （与 form 标量字段一致——FastAPI Form / Playwright FormData 提交时用原名，
    避免接口协议破坏）。``name`` 已是 snake_case 时裸 ``UploadFile``。

    字段名同样走 :func:`_to_field_name` 处理边界（hyphen / 关键字 / 数字开头等）。

    :param name: 原始 OpenAPI property 名称。
    :return: 字段声明字符串（snake_case 时裸 UploadFile，非 snake_case 时带 alias）。
    """
    field_name = _to_field_name(name)
    if _is_snake_case(name):
        return f"{field_name}: UploadFile"
    return f"{field_name}: Annotated[UploadFile, Field(serialization_alias={name!r})]"


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
