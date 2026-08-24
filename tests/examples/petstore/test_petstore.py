from stoma import ResponseSpec
from stoma.client import Client
from tests.examples.petstore.app.endpoints.get_order_by_id import GetOrderById
from tests.examples.petstore.app.endpoints.get_user_by_name import GetUserByName
from tests.examples.petstore.app.endpoints.login_user import LoginUser
from tests.examples.petstore.app.endpoints.logout_user import LogoutUser


def test_get_order_by_id_returns_order(e2e_client: Client) -> None:
    """GET /store/order/{orderId}：验证 path 参数插值与 Order schema 校验。"""
    endpoint = GetOrderById(order_id=10)
    response = e2e_client.send(endpoint)

    assert response.raw.status == 200
    order = response.expect(endpoint.on_200_application_json)
    assert order.status
    assert order.status.value == "approved"


def test_login_user_returns_token(e2e_client: Client) -> None:
    """GET /user/login：验证 query 参数拼接（username/password）。"""
    endpoint = LoginUser(username="alice", password="12345")
    response = e2e_client.send(endpoint)

    assert response.raw.status == 200
    body: str = response.expect(ResponseSpec(200, "*", expected_type=str))
    assert isinstance(body, str)
    assert "Logged in user session:" in body


def test_logout_user_returns_200(e2e_client: Client) -> None:
    """GET /user/logout：验证无副作用 logout 调用。"""
    endpoint = LogoutUser()
    response = e2e_client.send(endpoint)

    assert response.raw.status == 200


def test_get_user_by_name_returns_user(e2e_client: Client) -> None:
    """GET /user/{username}：验证 path 参数插值与 User schema 校验。"""
    endpoint = GetUserByName(username="user1")
    response = e2e_client.send(endpoint)

    user = response.expect(endpoint.on_200_application_json)
    assert user.username == "user1"


def test_get_user_by_name_returns_user2(e2e_client: Client) -> None:
    """GET /user/{username}：验证 user 端点对多个用户名的可用性（user2）。"""
    endpoint = GetUserByName(username="user2")
    response = e2e_client.send(endpoint)

    user = response.expect(endpoint.on_200_application_json)
    assert user.username == "user2"
