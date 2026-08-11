"""T015b: 测试路径参数插值逻辑。

验证 APIRoute._interpolate_path_params() 方法能够正确将路径中的
{param} 占位符替换为实际参数值。
"""

from typing import Annotated

from pydantic import BaseModel

from src.client import Client
from src import Path
from src.routing import APIRoute, APIRouter

# 创建测试用的路由器
router = APIRouter()


# 测试用的响应模型
class UserData(BaseModel):
    """用户数据模型。"""

    id: int
    name: str
    email: str


def test_interpolate_single_path_param() -> None:
    """测试单个路径参数的插值。"""

    @router.get("/users/{user_id}")
    class GetUser(APIRoute[UserData]):
        user_id: Annotated[int, Path()]

    # 创建实例并测试路径插值
    endpoint = GetUser(user_id=123)
    interpolated_path = Client(context=None)._interpolate_path_params(endpoint, endpoint._get_dependant())

    assert interpolated_path == "/users/123"


def test_interpolate_multiple_path_params() -> None:
    """测试多个路径参数的插值。"""

    @router.get("/users/{user_id}/posts/{post_id}")
    class GetUserPost(APIRoute[dict[str, str]]):
        user_id: Annotated[int, Path()]
        post_id: Annotated[int, Path()]

    # 创建实例并测试路径插值
    endpoint = GetUserPost(user_id=123, post_id=456)
    interpolated_path = Client(context=None)._interpolate_path_params(endpoint, endpoint._get_dependant())

    assert interpolated_path == "/users/123/posts/456"


def test_interpolate_path_with_string_param() -> None:
    """测试携带字符串参数的路径插值。"""

    @router.get("/posts/{slug}/comments/{comment_id}")
    class GetPostComment(APIRoute[dict[str, str]]):
        slug: Annotated[str, Path()]
        comment_id: Annotated[int, Path()]

    # 创建实例并测试路径插值
    endpoint = GetPostComment(slug="hello-world", comment_id=789)
    interpolated_path = Client(context=None)._interpolate_path_params(endpoint, endpoint._get_dependant())

    assert interpolated_path == "/posts/hello-world/comments/789"


def test_interpolate_path_with_mixed_params() -> None:
    """测试混合参数类型的路径插值。"""

    @router.put("/users/{user_id}/resource/{resource_id}/version/{version}")
    class UpdateResource(APIRoute[dict[str, str]]):
        user_id: Annotated[int, Path()]
        resource_id: Annotated[str, Path()]
        version: Annotated[int, Path()]

    # 创建实例并测试路径插值
    endpoint = UpdateResource(user_id=42, resource_id="abc123", version=2)
    interpolated_path = Client(context=None)._interpolate_path_params(endpoint, endpoint._get_dependant())

    assert interpolated_path == "/users/42/resource/abc123/version/2"


def test_interpolate_path_no_params() -> None:
    """测试没有路径参数的路径插值（应返回原始路径）。"""

    @router.get("/users")
    class ListUsers(APIRoute[list[UserData]]):
        limit: int = 20
        offset: int = 0

    # 创建实例并测试路径插值
    endpoint = ListUsers(limit=10, offset=5)
    interpolated_path = Client(context=None)._interpolate_path_params(endpoint, endpoint._get_dependant())

    assert interpolated_path == "/users"


def test_interpolate_path_preserves_base_path() -> None:
    """测试路径插值保留基础路径部分。"""

    @router.get("/api/v1/users/{user_id}")
    class GetUserV1(APIRoute[UserData]):
        user_id: Annotated[int, Path()]

    # 创建实例并测试路径插值
    endpoint = GetUserV1(user_id=999)
    interpolated_path = Client(context=None)._interpolate_path_params(endpoint, endpoint._get_dependant())

    assert interpolated_path == "/api/v1/users/999"
