"""T015c: 测试查询参数序列化逻辑。

验证 APIRoute._serialize_query_params() 方法能够正确将查询参数
转换为 URL query string 字典格式。
"""

from typing import Annotated

from pydantic import BaseModel

from src.client import Client
from src.params import Query
from src.routing import APIRoute, APIRouter

# 创建测试用的路由器
router = APIRouter()


# 测试用的响应模型
class UserData(BaseModel):
    """用户数据模型。"""

    id: int
    name: str
    email: str


def test_serialize_single_query_param() -> None:
    """测试单个查询参数的序列化。"""

    @router.get("/users")
    class GetUsers(APIRoute[list[UserData]]):
        limit: Annotated[int, Query()] = 20

    # 创建实例并测试查询参数序列化
    endpoint = GetUsers(limit=10)
    query_params = Client(context=None)._collect_query_params(endpoint, endpoint._get_dependant())

    assert query_params == {"limit": 10}


def test_serialize_multiple_query_params() -> None:
    """测试多个查询参数的序列化。"""

    @router.get("/users")
    class GetUsers(APIRoute[list[UserData]]):
        limit: Annotated[int, Query()] = 20
        offset: Annotated[int, Query()] = 0
        keyword: Annotated[str | None, Query()] = None

    # 创建实例并测试查询参数序列化
    endpoint = GetUsers(limit=50, offset=10, keyword="test")
    query_params = Client(context=None)._collect_query_params(endpoint, endpoint._get_dependant())

    # Playwright 在发送时会自动 str() 转换 int，bool 转 'true'/'false'
    assert query_params == {"limit": 50, "offset": 10, "keyword": "test"}


def test_serialize_query_params_skip_none() -> None:
    """测试查询参数序列化时跳过 None 值。"""

    @router.get("/search")
    class Search(APIRoute[list[UserData]]):
        query: Annotated[str, Query()]
        limit: Annotated[int, Query()] = 20
        filter_type: Annotated[str | None, Query()] = None

    # 创建实例（filter_type = None）
    endpoint = Search(query="hello", limit=25, filter_type=None)
    query_params = Client(context=None)._collect_query_params(endpoint, endpoint._get_dependant())

    # filter_type 应该被跳过（None）
    assert query_params == {"query": "hello", "limit": 25}
    assert "filter_type" not in query_params


def test_serialize_query_params_with_alias() -> None:
    """测试查询参数序列化时使用别名。"""

    @router.get("/users")
    class GetUsers(APIRoute[list[UserData]]):
        page_size: Annotated[int, Query(alias="pageSize")] = 20
        page_num: Annotated[int, Query(alias="pageNum")] = 1

    # 创建实例并测试查询参数序列化
    endpoint = GetUsers(page_size=50, page_num=2)
    query_params = Client(context=None)._collect_query_params(endpoint, endpoint._get_dependant())

    # 应该使用别名作为键
    assert query_params == {"pageSize": 50, "pageNum": 2}


def test_serialize_query_params_with_boolean() -> None:
    """测试查询参数序列化时处理布尔值（HTTP 约定小写）。"""

    @router.get("/users")
    class GetUsers(APIRoute[list[UserData]]):
        active: Annotated[bool, Query()] = True
        verified: Annotated[bool, Query()] = False

    # 创建实例并测试查询参数序列化
    endpoint = GetUsers(active=True, verified=False)
    query_params = Client(context=None)._collect_query_params(endpoint, endpoint._get_dependant())

    # bool 必须手动转 'true'/'false'（Playwright 会输出 Python "True"/"False"）
    assert query_params == {"active": "true", "verified": "false"}


def test_serialize_query_params_with_default_values() -> None:
    """测试查询参数序列化时使用默认值。"""

    @router.get("/users")
    class GetUsers(APIRoute[list[UserData]]):
        limit: Annotated[int, Query()] = 20
        offset: Annotated[int, Query()] = 0

    # 创建实例，使用默认值
    endpoint = GetUsers()
    query_params = Client(context=None)._collect_query_params(endpoint, endpoint._get_dependant())

    # 默认值直接传递，Playwright 自动 str() 转换
    assert query_params == {"limit": 20, "offset": 0}


def test_serialize_query_params_type_conversion() -> None:
    """测试查询参数：int/float/str 直接传递（Playwright 自动 str()）。"""

    @router.get("/data")
    class GetData(APIRoute[dict]):
        count: Annotated[int, Query()] = 1
        ratio: Annotated[float, Query()] = 1.5
        name: Annotated[str, Query()] = "default"

    # 创建实例
    endpoint = GetData(count=42, ratio=3.14, name="test")
    query_params = Client(context=None)._collect_query_params(endpoint, endpoint._get_dependant())

    # int/float/str 直接传递，不做 str() 转换
    assert query_params == {"count": 42, "ratio": 3.14, "name": "test"}
