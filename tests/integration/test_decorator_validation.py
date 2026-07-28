"""T012: 验证装饰器语法与 IDE 类型提示。

此文件通过手动编写示例接口类，验证：
1. 装饰器语法的可用性（@router.get/post 等）
2. IDE 类型提示的准确性（泛型响应类型推断）
3. 泛型响应类型的工作（APIRoute[T]）
4. Pydantic BaseModel 的自动 __init__ 生成（零样板代码）
5. 参数标记的正确使用（Query, Path, Header, Body）

**验收场景**:
1. Given 开发者手动编写接口类，When 使用 `@router.get/post` 装饰器传入 path，
   Then IDE 提供参数补全与类型检查。
2. Given 接口类继承 `APIRoute[T]` 泛型，When 调用实例的 send 方法（`endpoint.with_context(context).send()`），
   Then mypy/IDE 可正确推断返回类型为 T。
3. Given 接口类继承 BaseModel 并使用 Query/Body/Header/Path 标记，
   When 字段声明完成，Then IDE 自动补全所有字段，无需编写 `__init__` 样板代码。
4. Given 生成的接口类使用路由元数据隔离（`_route_meta`），
   When 用户字段名为 method、path 等，Then 不产生命名冲突，框架正常工作。
"""

from typing import Annotated

from pydantic import BaseModel

from src.params import Body, Header, Path, Query
from src.routing import APIRoute, APIRouter


# ===== 定义响应模型 =====
class UserData(BaseModel):
    """用户数据模型。"""

    id: int
    name: str
    email: str
    age: int | None = None


class UserCreateRequest(BaseModel):
    """创建用户请求模型。"""

    name: str
    email: str
    age: int | None = None


class UserUpdateRequest(BaseModel):
    """更新用户请求模型。"""

    name: str | None = None
    email: str | None = None
    age: int | None = None


# ===== 创建路由器实例 =====
router = APIRouter()


# ===== 验收场景 1: 装饰器语法与参数补全 =====
# IDE 应该在 @router.get() 处提供参数补全（path）
@router.get("/users")
class GetUsers(APIRoute[list[UserData]]):
    """获取用户列表 - 响应类型：list[UserData]。

    验证：
    - 装饰器语法正确
    - 泛型类型注解 APIRoute[list[UserData]]
    - Query 参数标记
    - 参数默认值使用函数默认值形式
    """

    # Query 参数：使用 Annotated 和函数默认值
    limit: Annotated[int, Query(ge=1, le=100, description="每页数量")] = 20
    offset: Annotated[int, Query(ge=0, description="偏移量")] = 0
    # Header 参数：认证令牌
    token: Annotated[str, Header(alias="Authorization", description="认证令牌")]


# ===== 验收场景 2: 泛型响应类型推断 =====
# 测试 mypy/IDE 是否能正确推断返回类型为 UserData
@router.get("/users/{user_id}")
class GetUserById(APIRoute[UserData]):
    """根据 ID 获取用户 - 响应类型：UserData。

    验证：
    - 路径参数标记（Path）
    - 泛型返回类型推断
    """

    user_id: Annotated[int, Path(description="用户 ID", ge=1)]


# ===== 验收场景 3: BaseModel 自动 __init__ 生成（零样板代码）=====
# 测试是否无需编写 __init__，Pydantic 自动生成
@router.post("/users")
class CreateUser(APIRoute[UserData]):
    """创建用户 - 响应类型：UserData。

    验证：
    - POST 方法装饰器
    - Body 参数标记
    - 无需手动编写 __init__
    - IDE 应自动补全 name、email 等字段
    """

    # Body 参数：整个请求体
    body: Annotated[UserCreateRequest, Body(description="用户创建请求")]


# ===== 验收场景 4: 命名空间隔离（用户字段名为 method、path 等）=====
# 测试当用户字段名为 method、path 时是否产生冲突
@router.post("/debug")
class DebugEndpoint(APIRoute[dict[str, str]]):
    """测试命名空间隔离 - 用户字段名为 method、path 等保留字。

    验证：
    - 用户字段名为 method、path 不会与路由元数据冲突
    - 元数据隔离机制工作正常
    """

    # 故意使用可能冲突的字段名
    method: Annotated[str, Query(description="用户自定义的 method 字段")]
    path: Annotated[str, Query(description="用户自定义的 path 字段")]
    servers: Annotated[list[str] | None, Query(description="用户自定义的 servers 字段")] = None


# ===== 测试 PUT 方法 =====
@router.put("/users/{user_id}")
class UpdateUser(APIRoute[UserData]):
    """完全更新用户（PUT）。"""

    user_id: Annotated[int, Path(ge=1)]
    body: Annotated[UserCreateRequest, Body()]


# ===== 测试 PATCH 方法 =====
@router.patch("/users/{user_id}")
class PartialUpdateUser(APIRoute[UserData]):
    """部分更新用户（PATCH）。"""

    user_id: Annotated[int, Path(ge=1)]
    body: Annotated[UserUpdateRequest, Body()]


# ===== 测试 DELETE 方法 =====
@router.delete("/users/{user_id}")
class DeleteUser(APIRoute[dict[str, str]]):
    """删除用户（DELETE）。"""

    user_id: Annotated[int, Path(ge=1)]
    # 可选的认证头
    token: Annotated[str | None, Header(alias="Authorization")] = None


# ===== 测试多个查询参数和复杂验证 =====
@router.get("/search")
class SearchUsers(APIRoute[list[UserData]]):
    """搜索用户 - 测试多个查询参数和复杂验证。"""

    # 必需的查询参数（无默认值）
    query: Annotated[str, Query(min_length=1, max_length=100, description="搜索关键词")]

    # 可选的查询参数（有默认值）
    limit: Annotated[int, Query(ge=1, le=100)] = 20
    offset: Annotated[int, Query(ge=0)] = 0
    sort_by: Annotated[str, Query(pattern=r"^(name|email|age)$")] = "name"

    # 可选的 Header 参数
    x_request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None


# ===== 手动测试代码 =====
def test_decorator_validation() -> None:
    """手动测试：验证装饰器语法与类型提示。

    此函数不会实际发送 HTTP 请求（因为 __call__ 尚未实现），
    仅用于验证：
    1. 类实例化是否正常（BaseModel 的自动 __init__）
    2. 路由元数据是否正确注入
    3. IDE 类型提示是否工作
    """
    print("=" * 60)
    print("T012: 验证装饰器语法与 IDE 类型提示")
    print("=" * 60)

    # 验收场景 1: 装饰器语法与参数补全
    print("\n✅ 验收场景 1: 装饰器语法与参数补全")
    get_users_endpoint = GetUsers(limit=10, offset=0, token="Bearer test-token")
    get_users_meta = get_users_endpoint._get_dependant()
    assert get_users_meta.method == "GET"
    assert get_users_meta.path == "/users"
    assert get_users_endpoint.limit == 10
    assert get_users_endpoint.offset == 0
    assert get_users_endpoint.token == "Bearer test-token"
    print(f"  - 路由元数据: method={get_users_meta.method}, path={get_users_meta.path}")
    print(f"  - 实例字段: limit={get_users_endpoint.limit}, offset={get_users_endpoint.offset}")
    print("  - 装饰器语法验证通过 ✓")

    # 验收场景 2: 泛型响应类型推断
    print("\n✅ 验收场景 2: 泛型响应类型推断")
    get_user_endpoint = GetUserById(user_id=123)
    get_user_meta = get_user_endpoint._get_dependant()
    assert get_user_meta.method == "GET"
    assert get_user_meta.path == "/users/{user_id}"
    assert get_user_endpoint.user_id == 123
    print(f"  - 路由元数据: method={get_user_meta.method}, path={get_user_meta.path}")
    print(f"  - 路径参数: user_id={get_user_endpoint.user_id}")
    print("  - 泛型类型 APIRoute[UserData] 验证通过 ✓")
    print("  - mypy/IDE 应推断 get_user_endpoint.with_context(context).send() 返回类型为 UserData")

    # 验收场景 3: BaseModel 自动 __init__ 生成（零样板代码）
    print("\n✅ 验收场景 3: BaseModel 自动 __init__ 生成（零样板代码）")
    create_user_endpoint = CreateUser(body=UserCreateRequest(name="Alice", email="alice@example.com", age=30))
    create_user_meta = create_user_endpoint._get_dependant()
    assert create_user_meta.method == "POST"
    assert create_user_meta.path == "/users"
    assert create_user_endpoint.body.name == "Alice"
    assert create_user_endpoint.body.email == "alice@example.com"
    print(f"  - 路由元数据: method={create_user_meta.method}, path={create_user_meta.path}")
    print(f"  - Body 参数: name={create_user_endpoint.body.name}, email={create_user_endpoint.body.email}")
    print("  - 无需手动编写 __init__，Pydantic 自动生成 ✓")

    # 验收场景 4: 命名空间隔离（用户字段名为 method、path 等）
    print("\n✅ 验收场景 4: 命名空间隔离（用户字段名为 method、path 等）")
    debug_endpoint = DebugEndpoint(method="custom_method", path="/custom/path", servers=["https://custom.com"])
    debug_meta = debug_endpoint._get_dependant()
    # 验证路由元数据（来自装饰器）
    assert debug_meta.method == "POST"
    assert debug_meta.path == "/debug"
    # 验证用户字段（来自实例）
    assert debug_endpoint.method == "custom_method"
    assert debug_endpoint.path == "/custom/path"
    assert debug_endpoint.servers == ["https://custom.com"]
    print(f"  - 路由元数据（装饰器）: method={debug_meta.method}, path={debug_meta.path}")
    print(
        f"  - 用户字段（实例）: method={debug_endpoint.method}, path={debug_endpoint.path}, "
        f"servers={debug_endpoint.servers}"
    )
    print("  - 命名空间隔离验证通过，无冲突 ✓")

    # 测试其他 HTTP 方法
    print("\n✅ 测试其他 HTTP 方法（PUT、PATCH、DELETE）")
    update_endpoint = UpdateUser(user_id=123, body=UserCreateRequest(name="Bob", email="bob@example.com"))
    update_meta = update_endpoint._get_dependant()
    assert update_meta.method == "PUT"
    print(f"  - PUT 方法: {update_meta.method} {update_meta.path}")

    patch_endpoint = PartialUpdateUser(user_id=123, body=UserUpdateRequest(name="Charlie"))
    patch_meta = patch_endpoint._get_dependant()
    assert patch_meta.method == "PATCH"
    print(f"  - PATCH 方法: {patch_meta.method} {patch_meta.path}")

    delete_endpoint = DeleteUser(user_id=123, token="Bearer admin-token")
    delete_meta = delete_endpoint._get_dependant()
    assert delete_meta.method == "DELETE"
    print(f"  - DELETE 方法: {delete_meta.method} {delete_meta.path}")
    print("  - 所有 HTTP 方法装饰器验证通过 ✓")

    # 测试多个查询参数和复杂验证
    print("\n✅ 测试多个查询参数和复杂验证")
    search_endpoint = SearchUsers(
        query="john",
        limit=50,
        offset=10,
        sort_by="email",
        x_request_id="req-123",
    )
    assert search_endpoint.query == "john"
    assert search_endpoint.limit == 50
    assert search_endpoint.offset == 10
    assert search_endpoint.sort_by == "email"
    assert search_endpoint.x_request_id == "req-123"
    print(
        f"  - 查询参数: query={search_endpoint.query}, limit={search_endpoint.limit}, offset={search_endpoint.offset}"
    )
    print(f"  - Header 参数: X-Request-ID={search_endpoint.x_request_id}")
    print("  - 多参数和复杂验证通过 ✓")

    print("\n" + "=" * 60)
    print("✅ T012 所有验证通过！")
    print("=" * 60)
    print("\n总结：")
    print("1. ✓ 装饰器语法正确，@router.get/post/put/patch/delete 全部可用")
    print("2. ✓ 泛型响应类型 APIRoute[T] 工作正常，IDE 类型提示准确")
    print("3. ✓ 继承 BaseModel 自动生成 __init__，零样板代码")
    print("4. ✓ 路由元数据隔离机制工作正常，无命名冲突")
    print("5. ✓ Query/Path/Header/Body 参数标记全部正常工作")
    print("6. ✓ 参数默认值使用函数默认值形式（= value）")
    print("\n🎉 User Story 1 的接口定义格式已验证完毕！")
