"""测试 OpenAPI schema 字段约束的生成结果。"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from src.cli import app


class TestFieldConstraints:
    """测试 OpenAPI schema 字段约束场景的生成结果。"""

    def test_enum_string_field(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 OpenAPI enum 字段生成 Pydantic StrEnum 类。

        回归测试：``datamodel-code-generator`` 对
        ``kind: { type: string, enum: [dog, cat] }`` 生成 StrEnum 类，
        stoma 端到端管线保留该输出。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Enum Test API
  version: "1.0.0"
paths:
  /pets:
    post:
      operationId: createPet
      summary: 创建宠物
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Pet'
      responses:
        "200":
          description: ok
components:
  schemas:
    Pet:
      type: object
      required: [kind]
      properties:
        kind:
          type: string
          enum:
            - dog
            - cat
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        models = (out_dir / "models.py").read_text(encoding="utf-8")

        # dmcg 0.72.2 默认行为：string enum 生成 StrEnum 类。
        # 验证 Pet.kind 字段类型为 Kind（StrEnum 子类）。
        assert "class Kind(StrEnum):" in models
        assert '    dog = "dog"' in models
        assert '    cat = "cat"' in models
        assert "class Pet(BaseModel):" in models
        assert "kind: Kind" in models

    def test_format_datetime_field(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 ``format: date-time`` 字段生成 ``AwareDatetime`` 类型注解。

        回归测试：``datamodel-code-generator`` 将 OpenAPI ``format: date-time``
        映射为 Pydantic v2 ``AwareDatetime`` 类型。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Datetime Field API
  version: "1.0.0"
paths:
  /items:
    post:
      operationId: createItem
      summary: 创建项目（含日期时间字段）
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [releaseDate]
              properties:
                releaseDate:
                  type: string
                  format: date-time
      responses:
        "200":
          description: ok
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        models = (out_dir / "models.py").read_text(encoding="utf-8")
        assert "AwareDatetime" in models

    def test_nullable_and_default_field(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 nullable: true 和 default: <v> 正确生成 Pydantic 字段。

        - nullable: true → str | None = None
        - default: last → str | None = "last"
        """
        spec = """\
openapi: 3.1.0
info:
  title: Cursor API
  version: "1.0.0"
paths:
  /cursors:
    post:
      operationId: createCursor
      summary: 创建游标
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                prev:
                  type: string
                  nullable: true
                next:
                  type: string
                  default: last
      responses:
        "200":
          description: ok
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "models.py").read_text(encoding="utf-8")
        assert "prev: str | None = None" in content
        assert 'next: str | None = "last"' in content

    def test_min_max_length_constraints(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 minimum/maximum/minLength/maxLength 约束被保留为 Pydantic v2 风格。

        ``src/openapi/model_generator.py`` 已启用 dmcg 的 ``field_constraints=True``
        + ``use_annotated=True``，约束字段以 ``Annotated[T, Field(...)]``
        形式输出（取代默认的 v1 风格 ``conint(...)``/``constr(...)``，也替代
        ``T = Field(...)`` 这种把类型与默认值揉在同一位置的写法）。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Constrained Fields API
  version: "1.0.0"
paths:
  /users:
    post:
      operationId: createUser
      summary: 创建用户
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - age
                - name
              properties:
                age:
                  type: integer
                  minimum: 0
                  maximum: 150
                name:
                  type: string
                  minLength: 1
                  maxLength: 50
      responses:
        "200":
          description: 成功
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output

        models_file = out_dir / "models.py"
        assert models_file.exists(), f"models.py not found in {out_dir}"

        content = models_file.read_text(encoding="utf-8")

        assert "Annotated[int, Field(ge=0, le=150)]" in content
        assert "Annotated[str, Field(max_length=50, min_length=1)]" in content
        assert "conint(" not in content
        assert "constr(" not in content
        assert "from typing import Annotated" in content

    def test_additional_properties_dict(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """验证 ``additionalProperties: { schema }`` 生成 ``dict[str, <type>]`` 注解。

        dmcg 0.72.2 将 OpenAPI 的 ``additionalProperties: { type: array, items: { type: string } }``
        映射为 Pydantic v2 的 ``dict[str, list[str]]`` 类型注解。
        """
        spec = """\
openapi: 3.1.0
info:
  title: FileSet API
  version: 1.0.0
paths:
  /filesets:
    post:
      operationId: createFileSet
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - tags
              properties:
                task_id:
                  type: string
                tags:
                  title: Dict of tags, each containing a list of file names
                  type: object
                  additionalProperties:
                    type: array
                    items:
                      type: string
      responses:
        "200":
          description: ok
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        models = (out_dir / "models.py").read_text(encoding="utf-8")
        # dmcg 0.72.2 emits: tags: dict[str, list[str]]
        assert "dict[" in models, "tags field should be typed as dict[str, ...]"
        assert "list[str]" in models, "tags field should be typed as dict[..., list[str]]"

    def test_format_uuid_and_byte_fields(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 ``format: uuid`` 生成 ``UUID``，``format: byte`` 生成 ``Base64Str``。

        dmcg 0.72.2 对 OpenAPI ``format: uuid`` → Pydantic ``UUID``，
        ``format: byte`` → Pydantic ``Base64Str``（不是内置 ``bytes``）。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Format Constraints API
  version: "1.0.0"
paths:
  /documents:
    post:
      operationId: createDocument
      summary: 创建文档
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [id, data]
              properties:
                id:
                  type: string
                  format: uuid
                data:
                  type: string
                  format: byte
      responses:
        "200":
          description: ok
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        models = (out_dir / "models.py").read_text(encoding="utf-8")

        # format: uuid → UUID（从 uuid 模块导入）。
        assert "UUID" in models
        # format: byte → Base64Str（不是内置 bytes）。
        assert "Base64Str" in models

    def test_read_only_and_write_only_fields(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """验证 OpenAPI ``readOnly`` / ``writeOnly`` 字段修饰符的 dmcg 默认行为。

        回归测试：在 ``src/openapi/model_generator.py:41-52`` 的固化参数下，
        dmcg 0.72.2 既不会保留 ``read_only=True`` / ``write_only=True``
        关键字，也不会把标记落到 ``json_schema_extra``（探查证据见
        ``/tmp/task-7-probe.txt``）。本测试固化这一现状，便于未来切换 dmcg
        标志或加自定义模板时回归告警。
        """
        spec = """\
openapi: 3.1.0
info:
  title: ReadOnly/WriteOnly Field API
  version: "1.0.0"
paths:
  /users:
    post:
      operationId: createUser
      summary: 创建用户（含只读/只写字段）
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [password]
              properties:
                id:
                  type: integer
                  readOnly: true
                password:
                  type: string
                  writeOnly: true
      responses:
        "200":
          description: ok
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        models = (out_dir / "models.py").read_text(encoding="utf-8")

        # 类由 operationId `createUser` 派生。
        assert "class CreateUserRequest(BaseModel):" in models

        # dmcg 0.72.2 默认行为：readOnly 字段变成可选，writeOnly 无痕迹。
        assert "id: int | None = None" in models
        assert "password: str" in models

        # 既不在 Field kwargs，也不会落到 json_schema_extra。
        assert "read_only" not in models
        assert "write_only" not in models
        assert "json_schema_extra" not in models

    def test_non_snake_case_field_uses_annotated_alias(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """验证非 snake_case 字段的 ``alias`` 以 ``Annotated[T, Field(...)]`` 形式输出。

        与 ``test_min_max_length_constraints`` 配对：
        ``field_constraints=True`` + ``use_annotated=True`` 不仅影响约束字段，
        也会让 ``alias`` 走同一个 ``Annotated`` 包装（PEP 593 idiom）。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Alias Annotated API
  version: "1.0.0"
paths:
  /profiles:
    post:
      operationId: createProfile
      summary: 创建 profile
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                firstName:
                  type: string
      responses:
        "200":
          description: ok
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "models.py").read_text(encoding="utf-8")

        assert 'first_name: Annotated[str | None, Field(alias="firstName")] = None' in content
        assert "from typing import Annotated" in content
