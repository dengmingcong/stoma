"""tests/examples/petstore/test_app - 5 个 store/user 匿名 e2e happy-path 场景。

覆盖 petstore3.swagger.io 公开 API 的核心端点：

| # | HTTP | 端点                    | 请求体类型 | 响应类型 | Schema 校验 | 覆盖点                       |
|---|------|-------------------------|------------|----------|-------------|------------------------------|
| 1 | GET  | /store/order/{orderId}  | 无         | JSON     | 是          | path 参数插值                |
| 2 | GET  | /user/login             | query      | 字符串   | 否          | query 拼接（username/password）|
| 3 | GET  | /user/logout            | 无         | 200      | 否          | 无副作用 GET                 |
| 4 | GET  | /user/{username}        | 无         | JSON     | 是          | path 参数 + User schema      |
| 5 | GET  | /user/{username}        | 无         | JSON     | 是          | path 参数 + User schema（user2）|

所有场景均为 2xx，刻意避开 OAuth2 / uploadFile / XML body 等已知限制。

由于 petstore3 公开服务器存在以下服务端问题，以下 4 个端点不在本测试覆盖范围内：
- GET /store/inventory — 服务器持续返回 500
- POST /store/order — 服务器持续返回 500
- POST /user/createWithList — 服务器持续返回 500
- DELETE /store/order/{orderId} — 服务器持续返回 500（订单不存在）

注意：
- test_get_order_by_id_returns_order 使用 ``order_id=10``（order_id=1 已被服务器清理）
- ``Client.send(endpoint)`` 返回 ``Response``，按需调用 ``response.expect(spec)`` 触发协议校验；
  本文件按 Wave 5 模式迁移，与 api_rest_sh/test_app.py 风格一致。

响应协议映射：
- GetOrderById / GetUserByName：spec 同时声明 ``application/json`` +
  ``application/xml``，渲染器生成 ``on_200_application_json`` 与
  ``on_200_application_xml`` 两条 spec；petstore3 服务端实际返回 JSON，测试用
  ``on_200_application_json``。
- LoginUser：spec 仅声明 ``application/xml``，渲染器生成 ``on_200_application_xml``
  （文本族 → ``ResponseSpec(200, "*", expected_type=str)`` ，``T=str``）。petstore3 服务端实际
  返回 ``"Logged in user session: <token>"`` 字符串，``T=str`` 协议正确接收。
- LogoutUser：spec 无 response content，渲染器不生成 spec。本测试用
  ``ResponseSpec(200, "*", expected_type=bytes)`` 兜底接收空字节
  （服务端返回 ``User logged out``，content-type 通常 ``text/plain``，
  bytes 协议容错接受任意 media type 与 body）。

注意：渲染器生成的 ``on_<status>`` 是实例 ``@property``（不是 ``ClassVar``），
因此访问必须通过 ``endpoint`` 实例（如 ``endpoint.on_200_application_json``），
不能直接通过类（``GetOrderById.on_200_application_json`` 会返回 property 描述符本身）。
"""

from __future__ import annotations

from stoma import ResponseSpec
from stoma.client import Client
from tests.examples.petstore.app.endpoints.get_order_by_id import GetOrderById
from tests.examples.petstore.app.endpoints.get_user_by_name import GetUserByName
from tests.examples.petstore.app.endpoints.login_user import LoginUser
from tests.examples.petstore.app.endpoints.logout_user import LogoutUser


def test_get_order_by_id_returns_order(e2e_client: Client) -> None:
    """GET /store/order/{orderId}：验证 path 参数插值与 Order schema 校验。

    使用 ``order_id=10``：petstore3 公开服务器对各 order_id 返回的数据不稳定——
    1/2 返回脏数据（status 不在 ``placed/approved/delivered`` 枚举里，触发 Pydantic
    ValidationError），3-9 返回 404；``order_id=10`` 在 2026-08 当下稳定返回
    ``status="approved"`` 完整 Order JSON。

    ``response.expect(endpoint.on_200_application_json)`` 选择 JSON 协议分支
    （服务端实际返回 ``application/json`` + ``Order`` JSON）。
    ``response.expect`` 的返回类型由 ``ResponseSpec[Order]`` 静态推断为
    ``Order``，访问 ``.status`` 等字段无需 ``isinstance`` 收窄——这是本次
    IDE 推断修复的核心收益。
    """
    endpoint = GetOrderById(order_id=10)
    response = e2e_client.send(endpoint)

    assert response.raw.status == 200
    order = response.expect(endpoint.on_200_application_json)
    assert order is not None
    assert order.status.value == "approved"


def test_login_user_returns_token(e2e_client: Client) -> None:
    """GET /user/login：验证 query 参数拼接（username/password）。

    petstore3 真实响应 ``Logged in user session: <token>``，content-type 为
    ``application/json``，body 为字符串字面量。spec 同时声明 ``application/xml``
    + ``application/json``（均为 primitive string schema），渲染器在 JSON 分支
    因无 model 可 import 跳过该 decl；XML 分支生成
    ``on_200_application_xml`` 但服务端返回 ``application/json``，严格 media-type
    匹配会失败。用 ``ResponseSpec(200, "*", expected_type=str)`` + ``*`` 通配接收任意 content-type
    的字符串 body，绕过 spec/实际不一致的限制。
    """
    endpoint = LoginUser(username="alice", password="12345")
    response = e2e_client.send(endpoint)

    assert response.raw.status == 200
    body: str = response.expect(ResponseSpec(200, "*", expected_type=str))
    assert isinstance(body, str)
    assert "Logged in user session:" in body


def test_logout_user_returns_200(e2e_client: Client) -> None:
    """GET /user/logout：验证无副作用 logout 调用。

    spec 无 response content → 渲染器不生成 spec。用
    ``ResponseSpec(200, "*", expected_type=bytes)`` 显式接收字节内容，容错任意
    content-type（服务端返回 ``User logged out``，media type 通常 text/plain）。
    """
    endpoint = LogoutUser()
    response = e2e_client.send(endpoint)

    assert response.raw.status == 200


def test_get_user_by_name_returns_user(e2e_client: Client) -> None:
    """GET /user/{username}：验证 path 参数插值与 User schema 校验。

    petstore3 对 ``user1``（spec 示例用户名）返回 200 完整 JSON；未知用户名返回 404。
    ``response.expect`` 的返回类型由 ``ResponseSpec[User]`` 静态推断为
    ``User``，访问 ``.username`` 等字段无需 ``isinstance`` 收窄。
    """
    endpoint = GetUserByName(username="user1")
    response = e2e_client.send(endpoint)

    assert response.raw.status == 200
    user = response.expect(endpoint.on_200_application_json)
    assert user is not None
    assert user.username == "user1"


def test_get_user_by_name_returns_user2(e2e_client: Client) -> None:
    """GET /user/{username}：验证 user 端点对多个用户名的可用性（user2）。

    与 test_get_user_by_name_returns_user 相同逻辑，验证 user 端点对 user2 同样返回 200
    完整 JSON schema。
    """
    endpoint = GetUserByName(username="user2")
    response = e2e_client.send(endpoint)

    assert response.raw.status == 200
    user = response.expect(endpoint.on_200_application_json)
    assert user is not None
    assert user.username == "user2"
