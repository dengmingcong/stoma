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

import warnings
from pathlib import Path
from typing import Any, Protocol

from jinja2 import Environment, FileSystemLoader, Template
from pydantic import BaseModel
from pydantic.alias_generators import to_snake

from src.exceptions import OpenAPISchemaError
from src.openapi.fields import (
    build_form_field_line,
    build_upload_file_field_line,
    resolve_array_type,
)
from src.openapi.media_type import is_json_media_type
from src.openapi.models import (
    BinaryRequestBodyFields,
    Endpoint,
    JSONRequestBodyFields,
    MultipartFormRequestBodyFields,
    RequestBodyFields,
    ScalarRequestBodyFields,
    UrlencodedFormRequestBodyFields,
)
from src.openapi.naming import is_snake_case, to_pascal_case
from src.openapi.parameters import build_content_type_header, make_param_fields
from src.openapi.request_body import (
    flatten_body_fields,
    get_media_type_schema,
    is_body_fields_use_field,
)
from src.openapi.schema import (
    has_combinator,
    is_binary_schema_dict,
    is_primitive_schema_dict,
)
from src.openapi.type_mapping import is_primitive_json_type, python_type_name
from src.openapi.version import Reference30, Reference31, SpecVersion


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

    :var Reference: 实例化时注入的 Reference 类，用于在 ``object`` 上做
        版本感知的 Reference ``isinstance`` 检测。
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
        self.multi_media_type_endpoints: list[dict[str, Any]] = []
        # 由 cli 在生成 models.py 后注入可用 class 名字集合
        # 若为 None 则不检查（向后兼容）
        self.available_models: set[str] | None = None
        # Response 模型在 models.py 中找不到时记录，与 multi_media_type_endpoints 同模式
        self.missing_response_models: list[dict[str, Any]] = []

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
        class_name = to_pascal_case(operation_id)
        file_name = f"{to_snake(operation_id)}.py"
        # 用户指定：变量名 json_reponse_types（按用户字面意思，含 typo"reponse"）
        json_reponse_types = self._get_json_response_types(endpoint.responses, endpoint)
        response_type = " | ".join(json_reponse_types) if json_reponse_types else ""
        body_fields_template = self._extract_request_body_info(endpoint.request_body, endpoint)
        header_fields, param_fields, uses_field_import = make_param_fields(endpoint.parameters)

        # 响应在前、请求体在后（保持 spec 顺序）；``dict.fromkeys`` 保序去重，避免重名重复 import。
        # model 名字来自 JSON body 路径（import_model），response 路径也独立收集。
        body_import_model: str | None = (
            body_fields_template.import_model if isinstance(body_fields_template, JSONRequestBodyFields) else None
        )
        models_for_import: list[str] = list(json_reponse_types)
        if body_import_model:
            models_for_import.append(body_import_model)
        imported_models = list(dict.fromkeys(models_for_import))

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
            header_fields.append(content_type_header)
            uses_field_import = uses_field_import or not is_snake_case("Content-Type")

        # body 字段（非 snake_case 时含 ``Field(serialization_alias=)``）也会触发 Field import。
        # 检查 4 类 body 字段字符串中是否含 ``Field(``，避免 multipart 纯文件场景漏 import。
        uses_field_import = uses_field_import or is_body_fields_use_field(body_template_vars)

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
            self.multi_media_type_endpoints.append(
                {
                    "method": endpoint.method,
                    "path": endpoint.path,
                    "all_media_types": all_media_types,
                    "selected_media_type": media_type,
                }
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

        :param expanded_schema_dict: jsonref 展开后的 schema 字典，可能为 ``None``。
        :return: :class:`UrlencodedFormRequestBodyFields`。
        """
        form_text_fields: list[str] = []
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
            form_text_fields.append(build_form_field_line(prop_name, py_type))

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
                form_file_fields.append(build_upload_file_field_line(prop_name))
                continue
            if prop_type == "array":
                py_type = resolve_array_type(prop_schema)
            else:
                py_type = python_type_name(prop_type)
            form_text_fields.append(build_form_field_line(prop_name, py_type))

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
        if not is_primitive_json_type(schema_type):
            msg = (
                f"Unsupported RAW body schema type: {schema_type!r}. "
                "Only primitive types (string/integer/number/boolean) are supported in non-JSON media types."
            )
            raise OpenAPISchemaError(msg)
        py_type = python_type_name(str(schema_type))
        scalar_field = f"body: Annotated[{py_type}, Body(media_type={media_type!r})]"
        return ScalarRequestBodyFields(scalar_field=scalar_field)

    def _get_json_response_types(
        self,
        responses: dict[str, Any] | None,
        endpoint: Endpoint[Any, Any, Any],
    ) -> list[str]:
        """提取响应模型名列表（也是要从 ``.models`` 导入的类名集合）。

        遍历所有 response 的所有 content media type，匹配 JSON 家族：
        - ``application/json``
        - ``application/*+json``（RFC 6839 structured syntax suffix，如
          ``application/problem+json``、``application/json-patch+json``）

        命名规则与之前一致（``$ref`` 取末段 PascalCase；inline object 用
        ``{PascalOpId}Response`` / ``{PascalOpId}Response{n}``）。返回的 list 后续
        在 :meth:`render` 中用 ``" | "`` join 成 Union 字符串供模板使用。

        :param responses: OpenAPI 响应字典（状态码 → Response 对象），可为
            ``None`` 或空。
        :param endpoint: 当前 :class:`Endpoint` IR 对象。
        :return: 响应模型名列表，无任何可命名响应时返回空列表。
        """
        if not responses:
            return []

        operation_id_pascal = to_pascal_case(endpoint.operation_id)
        inline_counter = 0
        ordered_names: list[str] = []

        for response in responses.values():
            content = getattr(response, "content", None) or {}
            # 修复 1：匹配所有 JSON 家族（application/json + application/*+json）
            json_content = next(
                (mt_obj for mt, mt_obj in content.items()
                 if is_json_media_type(mt)),
                None,
            )
            if not json_content:
                continue
            schema = getattr(json_content, "media_type_schema", None)
            if isinstance(schema, self.Reference):
                name = to_pascal_case(schema.ref.rsplit("/", 1)[-1])
            else:
                inline_counter += 1
                if inline_counter == 1:
                    name = f"{operation_id_pascal}Response"
                else:
                    name = f"{operation_id_pascal}Response{inline_counter - 1}"

            if self.available_models is not None and name not in self.available_models:
                self.missing_response_models.append({
                    "method": endpoint.method,
                    "path": endpoint.path,
                    "missing_model": name,
                })
                continue

            ordered_names.append(name)

        return list(dict.fromkeys(ordered_names))


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
