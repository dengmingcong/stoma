"""参数标记类型的单元测试。"""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

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
        path_param = Path()
        assert path_param.in_ == ParamTypes.path

    def test_path_in_model(self) -> None:
        """测试在 Pydantic 模型中使用 Path。"""

        class TestModel(BaseModel):
            user_id: Annotated[int, Path()]

        instance = TestModel(user_id=123)
        assert instance.user_id == 123


class TestQuery:
    """测试 Query 参数标记。"""

    def test_query_basic(self) -> None:
        """测试基本的 Query 参数。"""
        query_param = Query()
        assert query_param.in_ == ParamTypes.query

    def test_query_in_model(self) -> None:
        """测试在 Pydantic 模型中使用 Query。"""

        class TestModel(BaseModel):
            limit: Annotated[int, Query()] = 20
            offset: Annotated[int, Query()] = 0

        instance = TestModel()
        assert instance.limit == 20
        assert instance.offset == 0

        instance = TestModel(limit=50, offset=10)
        assert instance.limit == 50
        assert instance.offset == 10


class TestHeader:
    """测试 Header 参数标记。"""

    def test_header_basic(self) -> None:
        """测试基本的 Header 参数。"""
        header_param = Header()
        assert header_param.in_ == ParamTypes.header

    def test_header_in_model(self) -> None:
        """测试在 Pydantic 模型中使用 Header。"""

        class TestModel(BaseModel):
            model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

            authorization: Annotated[str, Header()] = Field(serialization_alias="Authorization")
            user_agent: Annotated[str | None, Header()] = None

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

    def test_body_with_embed(self) -> None:
        """测试 embed 参数。"""
        body_param = Body(embed=True)
        assert body_param.embed is True

    def test_body_in_model(self) -> None:
        """测试在 Pydantic 模型中使用 Body。"""

        class UserData(BaseModel):
            name: str
            email: str

        class TestModel(BaseModel):
            user: Annotated[UserData, Body()]

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
            model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

            post_id: Annotated[int, Path()]
            expand: Annotated[bool, Query()] = False
            authorization: Annotated[str, Header()] = Field(serialization_alias="Authorization")
            body: Annotated[RequestBody, Body()]

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

    def test_param_with_validation_in_field(self) -> None:
        """测试参数验证通过 Field 设置。"""

        class TestModel(BaseModel):
            limit: Annotated[int, Query()] = Field(ge=1, le=100, default=20)

        instance = TestModel()
        assert instance.limit == 20

        instance = TestModel(limit=50)
        assert instance.limit == 50
