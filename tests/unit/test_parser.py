"""测试 OpenAPI 解析器。

验证 prance $ref 展开后的解析结果。
"""

from __future__ import annotations

from pathlib import Path

from src.openapi.parser import OpenAPIParser


class TestParserRefResolution:
    """验证 prance 已展开 $ref 后，Parser 直接取值即可。"""

    def test_parameter_ref_is_resolved(self, tmp_path: Path) -> None:
        """验证 parameters 中的 $ref 已被 prance 展开为实际对象。"""
        spec = """\
openapi: 3.1.0
info:
  title: Ref Test
  version: "1.0.0"
paths:
  /items/{id}:
    get:
      operationId: getItem
      parameters:
        - $ref: '#/components/parameters/ItemId'
      responses:
        "200":
          description: ok
components:
  parameters:
    ItemId:
      name: id
      in: path
      required: true
      schema:
        type: string
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")

        parser = OpenAPIParser(spec_file)
        parser.load()
        parser.validate()
        endpoints = parser.get_endpoints()

        assert len(endpoints) == 1
        endpoint = endpoints[0]
        assert len(endpoint.parameters) == 1
        param = endpoint.parameters[0]
        # prance 展开后是实际 Parameter 对象，不再是 Reference。
        assert param.name == "id"
        assert param.param_in == "path"

    def test_request_body_ref_is_resolved(self, tmp_path: Path) -> None:
        """验证 requestBody $ref 已被 prance 展开为实际对象。"""
        spec = """\
openapi: 3.1.0
info:
  title: Ref Test
  version: "1.0.0"
paths:
  /users:
    post:
      operationId: createUser
      requestBody:
        $ref: '#/components/requestBodies/CreateUserRequest'
      responses:
        "200":
          description: ok
components:
  requestBodies:
    CreateUserRequest:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [name]
            properties:
              name:
                type: string
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")

        parser = OpenAPIParser(spec_file)
        parser.load()
        parser.validate()
        endpoints = parser.get_endpoints()

        assert len(endpoints) == 1
        endpoint = endpoints[0]
        assert endpoint.request_body is not None
        assert endpoint.request_body.required is True

    def test_response_ref_is_resolved(self, tmp_path: Path) -> None:
        """验证 response $ref 已被 prance 展开为实际对象。"""
        spec = """\
openapi: 3.1.0
info:
  title: Ref Test
  version: "1.0.0"
paths:
  /users/{id}:
    get:
      operationId: getUser
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: string
      responses:
        "200":
          $ref: '#/components/responses/UserResponse'
components:
  responses:
    UserResponse:
      description: ok
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/User'
  schemas:
    User:
      type: object
      properties:
        name:
          type: string
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")

        parser = OpenAPIParser(spec_file)
        parser.load()
        parser.validate()
        endpoints = parser.get_endpoints()

        assert len(endpoints) == 1
        endpoint = endpoints[0]
        assert endpoint.responses is not None
        assert "200" in endpoint.responses
        response = endpoint.responses["200"]
        # prance 展开后是实际 Response 对象。
        assert response.description == "ok"

    def test_nested_ref_in_schema_is_resolved(self, tmp_path: Path) -> None:
        """验证 schema 属性内的 $ref 也被 prance 递归展开。"""
        spec = """\
openapi: 3.1.0
info:
  title: Ref Test
  version: "1.0.0"
paths:
  /users:
    post:
      operationId: createUser
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CreateUserRequest'
      responses:
        "200":
          description: ok
components:
  schemas:
    CreateUserRequest:
      type: object
      required: [name]
      properties:
        name:
          type: string
        avatar:
          $ref: '#/components/schemas/Avatar'
    Avatar:
      type: object
      required: [url]
      properties:
        url:
          type: string
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")

        parser = OpenAPIParser(spec_file)
        parser.load()
        parser.validate()
        endpoints = parser.get_endpoints()

        assert len(endpoints) == 1
        endpoint = endpoints[0]
        rb = endpoint.request_body
        assert rb is not None
        content = rb.content
        schema = content["application/json"].media_type_schema
        # prance 递归展开后不再是 Reference，而是实际 Schema 对象。
        schema_dict = schema.model_dump()
        assert schema_dict["type"] == "object"

    def test_no_parameters_returns_empty_list(self, tmp_path: Path) -> None:
        """验证没有参数的 endpoint 返回空列表而非 None。"""
        spec = """\
openapi: 3.1.0
info:
  title: Ref Test
  version: "1.0.0"
paths:
  /health:
    get:
      operationId: health
      responses:
        "200":
          description: ok
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")

        parser = OpenAPIParser(spec_file)
        parser.load()
        parser.validate()
        endpoints = parser.get_endpoints()

        assert len(endpoints) == 1
        assert endpoints[0].parameters == []

    def test_no_request_body_returns_none(self, tmp_path: Path) -> None:
        """验证没有 requestBody 的 endpoint 返回 None。"""
        spec = """\
openapi: 3.1.0
info:
  title: Ref Test
  version: "1.0.0"
paths:
  /health:
    get:
      operationId: health
      responses:
        "200":
          description: ok
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")

        parser = OpenAPIParser(spec_file)
        parser.load()
        parser.validate()
        endpoints = parser.get_endpoints()

        assert len(endpoints) == 1
        assert endpoints[0].request_body is None

    def test_only_default_response(self, tmp_path: Path) -> None:
        """验证只有 default 响应时的处理。

        OpenAPI 允许只有 default 响应（无具体状态码）。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Ref Test
  version: "1.0.0"
paths:
  /health:
    delete:
      operationId: deleteHealth
      responses:
        default:
          description: ok
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")

        parser = OpenAPIParser(spec_file)
        parser.load()
        parser.validate()
        endpoints = parser.get_endpoints()

        assert len(endpoints) == 1
        assert endpoints[0].responses is not None
        assert "default" in endpoints[0].responses
