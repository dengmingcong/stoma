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
- test_get_order_by_id_returns_order 使用 ``order_id=2``（order_id=1 已被服务器清理）
- test_login_user_returns_token 和 test_logout_user_returns_200 的响应 body 为裸字符串
  （如 ``"Logged in user session: 12345"``），stoma 的 build_response 可以处理这种情况
"""

from __future__ import annotations

from stoma.client import Client
from tests.examples.petstore.app.get_order_by_id import GetOrderById
from tests.examples.petstore.app.get_user_by_name import GetUserByName
from tests.examples.petstore.app.login_user import LoginUser
from tests.examples.petstore.app.logout_user import LogoutUser
from tests.examples.petstore.app.models import Order, User


def test_get_order_by_id_returns_order(e2e_client: Client) -> None:
    """GET /store/order/{orderId}：验证 path 参数插值与 Order schema 校验。

    使用 ``order_id=2``——order_id=1 已被服务端清理，会返回 500；
    其他 ID 也可能返回 500，仅 ``order_id=2`` 在 2026-08-20 当下稳定可用。
    """
    response = e2e_client.send(GetOrderById(order_id=2))

    assert response.raw.status == 200
    assert response.validated is not None
    assert isinstance(response.validated, Order)


def test_login_user_returns_token(e2e_client: Client) -> None:
    """GET /user/login：验证 query 参数拼接（username/password）。

    petstore3 真实响应 ``Logged in user session: <token>``，content-type 为
    ``application/json``，但 body 不是合法 JSON 字符串字面量。
    stoma 的 build_response 可以处理这种裸字符串响应。
    """
    response = e2e_client.send(LoginUser(username="alice", password="12345"))

    assert response.raw.status == 200


def test_logout_user_returns_200(e2e_client: Client) -> None:
    """GET /user/logout：验证无副作用 logout 调用。

    petstore3 真实响应 ``User logged out``，content-type 为 ``application/json``，
    但 body 不是合法 JSON 字符串字面量。
    stoma 的 build_response 可以处理这种裸字符串响应。
    """
    response = e2e_client.send(LogoutUser())

    assert response.raw.status == 200


def test_get_user_by_name_returns_user(e2e_client: Client) -> None:
    """GET /user/{username}：验证 path 参数插值与 User schema 校验。

    petstore3 对 ``user1``（spec 示例用户名）返回 200 完整 JSON；未知用户名返回 404。
    """
    response = e2e_client.send(GetUserByName(username="user1"))

    assert response.raw.status == 200
    assert response.validated is not None
    assert isinstance(response.validated, User)


def test_get_user_by_name_returns_user2(e2e_client: Client) -> None:
    """GET /user/{username}：验证 user 端点对多个用户名的可用性（user2）。

    与 test_get_user_by_name_returns_user 相同逻辑，验证 user 端点对 user2 同样返回 200
    完整 JSON schema。
    """
    response = e2e_client.send(GetUserByName(username="user2"))

    assert response.raw.status == 200
    assert response.validated is not None
    assert isinstance(response.validated, User)
