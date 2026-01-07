"""参数标记类型的单元测试。"""

from typing import Annotated

import pytest
from pydantic import BaseModel, ValidationError

from src.params import Body, Header, ParamTypes, Path, Query


class TestParamTypes:
    """测试 ParamTypes 枚举。"""

    def test_param_types_values(self) -> None:
        """验证参数类型枚举值。"""
        assert ParamTypes.query.value == "query"
        assert ParamTypes.header.value == "header"
        assert ParamTypes.path.value == "path"
        assert ParamTypes.body.value == "body"


class TestPath:
    """测试 Path 参数标记。"""

    def test_path_basic(self) -> None:
        """测试基本的 Path 参数。"""
        from pydantic_core import PydanticUndefined

        path_param = Path(description="用户 ID")
        assert path_param.in_ == ParamTypes.path
        assert path_param.description == "用户 ID"
        assert path_param.default is PydanticUndefined

    def test_path_with_validation(self) -> None:
        """测试带验证规则的 Path 参数。"""
        path_param = Path(gt=0, le=1000, description="必须在 1-1000 之间")
        # 验证约束存储在 metadata 中
        assert any(constraint.gt == 0 for constraint in path_param.metadata if hasattr(constraint, "gt"))
        assert any(constraint.le == 1000 for constraint in path_param.metadata if hasattr(constraint, "le"))

    def test_path_in_model(self) -> None:
        """测试在 Pydantic 模型中使用 Path。"""

        class TestModel(BaseModel):
            user_id: Annotated[int, Path(description="用户 ID", gt=0)]

        # 创建实例
        instance = TestModel(user_id=123)
        assert instance.user_id == 123

        # 验证失败
        with pytest.raises(ValidationError):
            TestModel(user_id=0)  # 违反 gt=0


class TestQuery:
    """测试 Query 参数标记。"""

    def test_query_basic(self) -> None:
        """测试基本的 Query 参数。"""
        from pydantic_core import PydanticUndefined

        query_param = Query(description="分页大小")
        assert query_param.in_ == ParamTypes.query
        assert query_param.description == "分页大小"
        # Query 不提供 default 参数，应使用函数参数默认值
        assert query_param.default is PydanticUndefined

    def test_query_with_validation(self) -> None:
        """测试带验证规则的 Query 参数。"""
        from pydantic_core import PydanticUndefined

        query_param = Query(ge=1, le=100)
        assert query_param.default is PydanticUndefined
        # 验证约束存储在 metadata 中
        assert any(constraint.ge == 1 for constraint in query_param.metadata if hasattr(constraint, "ge"))
        assert any(constraint.le == 100 for constraint in query_param.metadata if hasattr(constraint, "le"))

    def test_query_in_model(self) -> None:
        """测试在 Pydantic 模型中使用 Query。"""

        class TestModel(BaseModel):
            limit: Annotated[int, Query(ge=1, le=100)] = 20
            offset: Annotated[int, Query(ge=0)] = 0

        # 使用默认值
        instance = TestModel()
        assert instance.limit == 20
        assert instance.offset == 0

        # 自定义值
        instance = TestModel(limit=50, offset=10)
        assert instance.limit == 50
        assert instance.offset == 10

        # 验证失败
        with pytest.raises(ValidationError):
            TestModel(limit=101)  # 违反 le=100


class TestHeader:
    """测试 Header 参数标记。"""

    def test_header_basic(self) -> None:
        """测试基本的 Header 参数。"""
        header_param = Header(alias="Authorization")
        assert header_param.in_ == ParamTypes.header
        assert header_param.alias == "Authorization"
        assert header_param.convert_underscores is True

    def test_header_with_convert_underscores(self) -> None:
        """测试 convert_underscores 参数。"""
        header_param = Header(convert_underscores=False)
        assert header_param.convert_underscores is False

    def test_header_in_model(self) -> None:
        """测试在 Pydantic 模型中使用 Header。"""

        class TestModel(BaseModel):
            authorization: Annotated[str, Header(alias="Authorization")]
            user_agent: Annotated[str | None, Header()] = None

        # 创建实例
        instance = TestModel(authorization="Bearer token")
        assert instance.authorization == "Bearer token"
        assert instance.user_agent is None


class TestBody:
    """测试 Body 参数标记。"""

    def test_body_basic(self) -> None:
        """测试基本的 Body 参数。"""
        body_param = Body()
        assert body_param.in_ == ParamTypes.body
        assert body_param.embed is False
        assert body_param.media_type == "application/json"

    def test_body_with_embed(self) -> None:
        """测试 embed 参数。"""
        body_param = Body(embed=True)
        assert body_param.embed is True

    def test_body_with_custom_media_type(self) -> None:
        """测试自定义媒体类型。"""
        body_param = Body(media_type="application/xml")
        assert body_param.media_type == "application/xml"

    def test_body_in_model(self) -> None:
        """测试在 Pydantic 模型中使用 Body。"""

        class UserData(BaseModel):
            name: str
            email: str

        class TestModel(BaseModel):
            user: Annotated[UserData, Body()]

        # 创建实例
        user_data = UserData(name="Alice", email="alice@example.com")
        instance = TestModel(user=user_data)
        assert instance.user.name == "Alice"
        assert instance.user.email == "alice@example.com"


class TestParamIntegration:
    """测试参数的综合使用。"""

    def test_mixed_params_in_model(self) -> None:
        """测试在一个模型中混合使用不同类型的参数。"""

        class RequestBody(BaseModel):
            title: str
            content: str

        class TestEndpoint(BaseModel):
            post_id: Annotated[int, Path(description="文章 ID", gt=0)]
            expand: Annotated[bool, Query(description="是否展开")] = False
            authorization: Annotated[str, Header(alias="Authorization")]
            body: Annotated[RequestBody, Body()]

        # 创建实例
        request_body = RequestBody(title="Test", content="Content")
        instance = TestEndpoint(
            post_id=123,
            expand=True,
            authorization="Bearer token",
            body=request_body,
        )

        assert instance.post_id == 123
        assert instance.expand is True
        assert instance.authorization == "Bearer token"
        assert instance.body.title == "Test"

    def test_param_with_examples(self) -> None:
        """测试参数的 examples 属性。"""
        query_param = Query(examples=[10, 20, 50, 100])
        # examples 存储在我们自定义的属性中
        assert hasattr(query_param, "examples")
        assert query_param.examples == [10, 20, 50, 100]

    def test_param_with_deprecated(self) -> None:
        """测试参数的 deprecated 属性。"""
        query_param = Query(deprecated=True)
        assert query_param.deprecated is True

    def test_param_with_json_schema_extra(self) -> None:
        """测试参数的 json_schema_extra 属性。"""
        query_param = Query(json_schema_extra={"x-custom": "value"})
        assert query_param.json_schema_extra == {"x-custom": "value"}
