"""测试 form-urlencoded / multipart / scalar JSON / binary 请求体的 CLI 生成结果。"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from src.cli import app


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
        """验证 application/x-www-form-urlencoded 单标量字段生成 Annotated[str, Form()]。"""
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
        compile(content, "add_scores.py", "exec")

    def test_multipart_single_file(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 multipart/form-data 含 format: binary 单文件字段生成 UploadFile（无 Form import）。"""
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
        # multipart 文件场景不应导入 Form
        assert "Form" not in content
        compile(content, "upload_avatar.py", "exec")

    def test_multipart_form_file_mix(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 multipart/form-data 混合标量 + binary 字段同时生成 Form 和 UploadFile。"""
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
        assert "Form" in content
        assert "UploadFile" in content
        compile(content, "upload_with_form.py", "exec")

    def test_scalar_json_integer(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 application/json 含 integer scalar schema 生成 Annotated[int, Body()]。"""
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
        assert "importance: Annotated[int, Body()]" in content
        assert "from stoma import APIRouter, APIRoute, Body" in content
        compile(content, "set_importance.py", "exec")

    def test_scalar_json_string(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 application/json 含 string scalar schema 生成 Annotated[str, Body()]。"""
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
        assert "scalar: Annotated[str, Body()]" in content
        assert "from stoma import APIRouter, APIRoute, Body" in content
        compile(content, "post_scalar.py", "exec")

    def test_binary_octet_stream(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 application/octet-stream 生成 UploadFile + upload_as_multipart=False。"""
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
        assert "upload_raw: UploadFile" in content
        assert "upload_as_multipart=False" in content
        assert "from stoma import APIRouter, APIRoute, Body, UploadFile" in content
        compile(content, "upload_raw.py", "exec")

    def test_binary_image_png(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 image/png 生成 UploadFile + upload_as_multipart=False。"""
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
        assert "upload_image: UploadFile" in content
        assert "upload_as_multipart=False" in content
        assert "from stoma import APIRouter, APIRoute, Body, UploadFile" in content
        compile(content, "upload_image.py", "exec")
