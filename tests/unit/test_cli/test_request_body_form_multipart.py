"""测试 form-urlencoded / multipart / scalar JSON / binary 请求体的 CLI 生成结果。"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from src.cli import app

# 字段声明过长，提取为模块级常量便于复用并满足 line-length 限制。
_CONTENT_TYPE_LINE_TEMPLATE: str = (
    "content_type: Annotated[str, Header(), "
    'Field(serialization_alias="Content-Type")] = "{media_type}"'
)


def _content_type_line(media_type: str) -> str:
    """生成 auto Content-Type 字段声明的完整字符串。"""
    return _CONTENT_TYPE_LINE_TEMPLATE.format(media_type=media_type)


def _build_spec(
    path: str, method: str, operation_id: str, request_body_block: str, components_block: str = ""
) -> str:
    """构造一个包含 requestBody 的 OpenAPI 3.1 规范。"""
    return f"""\
openapi: 3.1.0
info:
  title: Body API
  version: "1.0.0"
paths:
  {path}:
    {method}:
      operationId: {operation_id}
      summary: 测试
      requestBody:
{request_body_block}
      responses:
        "200":
          description: ok
{components_block}
"""


class TestMakeRequestBodyFormMultipart:
    """测试 form-urlencoded / multipart / scalar JSON / binary 请求体的生成结果。"""

    def test_form_urlencoded_scalar(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 application/x-www-form-urlencoded 单标量字段生成 Annotated[str, Form()]。

        Content-Type 由 Playwright 根据 ``form`` 参数自动派生，renderer 不注入。
        """
        spec = _build_spec(
            "/login",
            "post",
            "loginUser",
            """\
        required: true
        content:
          application/x-www-form-urlencoded:
            schema:
              type: object
              properties:
                username:
                  type: string
                password:
                  type: string
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "login_user.py").read_text(encoding="utf-8")
        assert "username: Annotated[str, Form()]" in content
        assert "password: Annotated[str, Form()]" in content
        assert "from stoma import APIRouter, APIRoute, Form" in content
        # 无 auto Content-Type，Playwright 自己设置
        assert "content_type" not in content
        compile(content, "login_user.py", "exec")

    def test_form_urlencoded_array(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 form-urlencoded 含数组字段时派生 list[T]（从 items.type 取元素类型）。"""
        spec = _build_spec(
            "/tags",
            "post",
            "addTags",
            """\
        required: true
        content:
          application/x-www-form-urlencoded:
            schema:
              type: object
              properties:
                tags:
                  type: array
                  items:
                    type: string
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "add_tags.py").read_text(encoding="utf-8")
        # 数组字段从 items.type 派生 list[T];与 runtime Annotated[list[str], Form()] 一致
        assert "tags: Annotated[list[str], Form()]" in content
        assert "from stoma import APIRouter, APIRoute, Form" in content
        assert "content_type" not in content
        compile(content, "add_tags.py", "exec")

    def test_form_urlencoded_array_with_int_items(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """验证 form-urlencoded 数组字段以 items.type 为元素类型派生 list[int]。"""
        spec = _build_spec(
            "/scores",
            "post",
            "addScores",
            """\
        required: true
        content:
          application/x-www-form-urlencoded:
            schema:
              type: object
              properties:
                scores:
                  type: array
                  items:
                    type: integer
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "add_scores.py").read_text(encoding="utf-8")
        # items.type=integer → list[int]
        assert "scores: Annotated[list[int], Form()]" in content
        assert "from stoma import APIRouter, APIRoute, Form" in content
        assert "content_type" not in content
        compile(content, "add_scores.py", "exec")

    def test_multipart_single_file(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 multipart/form-data 含 format: binary 单文件字段生成 UploadFile（无 Form import）。

        Content-Type（含 boundary）由 Playwright 自动设置，renderer 不注入。
        """
        spec = _build_spec(
            "/upload",
            "post",
            "uploadAvatar",
            """\
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                avatar:
                  type: string
                  format: binary
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "upload_avatar.py").read_text(encoding="utf-8")
        assert "avatar: UploadFile" in content
        assert "from stoma import APIRouter, APIRoute, UploadFile" in content
        # 无 auto Content-Type，Playwright 自己设置
        assert "content_type" not in content
        # multipart 文件场景不应导入 Form
        assert "Form" not in content
        compile(content, "upload_avatar.py", "exec")

    def test_multipart_form_file_mix(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 multipart/form-data 混合标量 + binary 字段同时生成 Form 和 UploadFile。

        Content-Type（含 boundary）由 Playwright 自动设置，renderer 不注入。
        """
        spec = _build_spec(
            "/upload-mix",
            "post",
            "uploadWithForm",
            """\
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                username:
                  type: string
                avatar:
                  type: string
                  format: binary
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "upload_with_form.py").read_text(encoding="utf-8")
        assert "username: Annotated[str, Form()]" in content
        assert "avatar: UploadFile" in content
        assert "from stoma import APIRouter, APIRoute, Form, UploadFile" in content
        assert "content_type" not in content
        compile(content, "upload_with_form.py", "exec")

    def test_scalar_json_integer(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 application/json 含 integer scalar schema 生成 ``body: Annotated[int, Body()]``。

        字段名固定为 ``body``（不受 operation_id 是否 snake_case 影响），避免
        非 snake_case 时追加 ``Field(serialization_alias=...)`` 的副作用。
        """
        spec = _build_spec(
            "/importance",
            "post",
            "setImportance",
            """\
        required: true
        content:
          application/json:
            schema:
              type: integer
""",
            components_block="""\
components:
  schemas:
    _Dummy:
      type: object
      properties:
        dummy:
          type: string
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "set_importance.py").read_text(encoding="utf-8")
        assert "body: Annotated[int, Body()]" in content
        # auto Content-Type header 触发 Header + Field import
        assert "from pydantic import Field" in content
        assert "from stoma import APIRouter, APIRoute, Header, Body" in content
        assert _content_type_line("application/json") in content
        compile(content, "set_importance.py", "exec")

    def test_scalar_json_string(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 application/json 含 string scalar schema 生成 ``body: Annotated[str, Body()]``。

        字段名固定为 ``body``（不受 operation_id 是否 snake_case 影响）。
        """
        spec = _build_spec(
            "/scalar",
            "post",
            "postScalar",
            """\
        required: true
        content:
          application/json:
            schema:
              type: string
""",
            components_block="""\
components:
  schemas:
    _Dummy:
      type: object
      properties:
        dummy:
          type: string
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "post_scalar.py").read_text(encoding="utf-8")
        assert "body: Annotated[str, Body()]" in content
        # auto Content-Type header 触发 Header + Field import
        assert "from pydantic import Field" in content
        assert "from stoma import APIRouter, APIRoute, Header, Body" in content
        assert _content_type_line("application/json") in content
        compile(content, "post_scalar.py", "exec")

    def test_binary_octet_stream(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 application/octet-stream 生成 ``body: UploadFile`` + ``upload_as_multipart=False``。

        字段名固定为 ``body``（不受 operation_id 是否 snake_case 影响）。
        """
        spec = _build_spec(
            "/raw",
            "post",
            "uploadRaw",
            """\
        required: true
        content:
          application/octet-stream:
            schema:
              type: string
              format: binary
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "upload_raw.py").read_text(encoding="utf-8")
        assert "body: UploadFile" in content
        assert "upload_as_multipart=False" in content
        # auto Content-Type header 触发 Header + Field import
        assert "from pydantic import Field" in content
        assert "from stoma import APIRouter, APIRoute, Header, UploadFile" in content
        assert _content_type_line("application/octet-stream") in content
        compile(content, "upload_raw.py", "exec")

    def test_binary_image_png(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 image/png 生成 ``body: UploadFile`` + ``upload_as_multipart=False``。

        字段名固定为 ``body``。
        """
        spec = _build_spec(
            "/image",
            "post",
            "uploadImage",
            """\
        required: true
        content:
          image/png:
            schema:
              type: string
              format: binary
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "upload_image.py").read_text(encoding="utf-8")
        assert "body: UploadFile" in content
        assert "upload_as_multipart=False" in content
        # auto Content-Type header 触发 Header + Field import
        assert "from pydantic import Field" in content
        assert "from stoma import APIRouter, APIRoute, Header, UploadFile" in content
        assert _content_type_line("image/png") in content
        compile(content, "upload_image.py", "exec")

    def test_form_urlencoded_non_snake_case_field(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 urlencoded form 字段名非 snake_case 时自动加 ``Field(serialization_alias=...)`` 保留原名。"""
        spec = _build_spec(
            "/submit",
            "post",
            "submitForm",
            """\
        required: true
        content:
          application/x-www-form-urlencoded:
            schema:
              type: object
              properties:
                user-name:
                  type: string
                X-API-Key:
                  type: string
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "submit_form.py").read_text(encoding="utf-8")
        # 非 snake_case 字段自动加 serialization_alias 保留原名
        assert "user_name: Annotated[str, Form(), Field(serialization_alias='user-name')]" in content
        assert "x_api_key: Annotated[str, Form(), Field(serialization_alias='X-API-Key')]" in content
        compile(content, "submit_form.py", "exec")

    def test_multipart_form_non_snake_case_field(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 multipart form 标量字段非 snake_case 时同样加 ``Field(serialization_alias=...)``。"""
        spec = _build_spec(
            "/upload-attrs",
            "post",
            "uploadWithAttrs",
            """\
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                user-name:
                  type: string
                file:
                  type: string
                  format: binary
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "upload_with_attrs.py").read_text(encoding="utf-8")
        # multipart 标量字段非 snake_case 时加 alias
        assert "user_name: Annotated[str, Form(), Field(serialization_alias='user-name')]" in content
        # file 字段保持裸 UploadFile（无 alias）
        assert "file: UploadFile" in content
        compile(content, "upload_with_attrs.py", "exec")

    def test_urlencoded_form_binary_field_emits_warning(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 urlencoded form 含 ``format=binary`` 字段时 emit ``UserWarning``（不抛错）。"""
        spec = _build_spec(
            "/mixed-bad",
            "post",
            "submitMixed",
            """\
        required: true
        content:
          application/x-www-form-urlencoded:
            schema:
              type: object
              properties:
                username:
                  type: string
                avatar:
                  type: string
                  format: binary
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        with pytest.warns(UserWarning, match="format=binary"):
            result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        # CLI 仍正常退出，form 字段被渲染
        assert result.exit_code == 0, result.output
        content = (out_dir / "submit_mixed.py").read_text(encoding="utf-8")
        assert "username: Annotated[str, Form()]" in content
        # urlencoded binary 字段退化为 form 标量（不再引发额外 side-effect）
        assert "avatar: Annotated[str, Form()]" in content
        compile(content, "submit_mixed.py", "exec")

    def test_multiple_media_types_raises_schema_error(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """验证 requestBody 含多个 media type 时抛出 ``OpenAPISchemaError``（stoma 不支持）。"""
        spec = _build_spec(
            "/ambiguous",
            "post",
            "ambiguousBody",
            """\
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                name:
                  type: string
          multipart/form-data:
            schema:
              type: object
              properties:
                file:
                  type: string
                  format: binary
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])
        # CLI 退出码非零（codegen 报错）
        assert result.exit_code != 0
        # 错误信息提示多 media type（来自 result.exception 或 output）
        error_repr = repr(result.exception) if result.exception else result.output
        assert "Multiple media types" in error_repr

    def test_multipart_file_field_non_snake_case_property(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 multipart file property 名非 snake_case 时自动加 ``Field(serialization_alias=...)``。

        对应第三轮 follow-up ⑥：``_build_upload_file_field_line`` 现在对非 snake_case
        字段名追加 ``Field(serialization_alias=<origin>)``，与 form 标量字段一致。
        """
        spec = _build_spec(
            "/upload-non-snake",
            "post",
            "uploadNonSnake",
            """\
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                avatar-file:
                  type: string
                  format: binary
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "upload_non_snake.py").read_text(encoding="utf-8")
        assert "avatar_file: Annotated[UploadFile, Field(serialization_alias='avatar-file')]" in content
        assert "from pydantic import Field" in content
        assert "from stoma import APIRouter, APIRoute, UploadFile" in content
        assert "content_type" not in content
        compile(content, "upload_non_snake.py", "exec")

    def test_binary_non_snake_case_operation_id(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 binary body 字段名固定为 ``body``，不受 operation_id snake_case 影响。

        原行为：按 operation_id 派生 field name，非 snake_case 时追加
        ``Field(serialization_alias=<origin>)``。新行为：固定 ``body: UploadFile``，
        无 alias。
        """
        spec = _build_spec(
            "/file",
            "post",
            "uploadFile",
            """\
        required: true
        content:
          application/octet-stream:
            schema:
              type: string
              format: binary
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "upload_file.py").read_text(encoding="utf-8")
        assert "body: UploadFile" in content
        assert "upload_as_multipart=False" in content
        # auto Content-Type header 触发 Header + Field import
        assert "from pydantic import Field" in content
        assert "from stoma import APIRouter, APIRoute, Header, UploadFile" in content
        compile(content, "upload_file.py", "exec")
