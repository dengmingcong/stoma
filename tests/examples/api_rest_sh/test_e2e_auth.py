"""examples/api_rest_sh/test_e2e_auth.py。

4 个鉴权 e2e 场景，打到真实 api.rest.sh：

| # | Endpoint                       | Auth scheme       | 凭证                               |
|---|--------------------------------|------------------|-----------------------------------|
| 1 | GET /auth/bearer               | Bearer           | Authorization: Bearer docs-token   |
| 2 | GET /auth/api-key-header       | API Key (header) | X-API-Key: docs-key               |
| 3 | GET /auth/basic                | Basic            | Authorization: Basic base64(docs:docs) |
| 4 | GET /auth/api-key-query        | API Key (query)  | api_key=docs-query-key             |

api.rest.sh 接受任意凭证通过鉴权端点（用于演示）。默认凭证从 spec x-cli-config 段读取。
"""
from __future__ import annotations

from stoma.client import Client
from tests.examples.api_rest_sh.app.get_auth_api_key_header import GetAuthApiKeyHeader
from tests.examples.api_rest_sh.app.get_auth_api_key_query import GetAuthApiKeyQuery
from tests.examples.api_rest_sh.app.get_auth_basic import GetAuthBasic
from tests.examples.api_rest_sh.app.get_auth_bearer import GetAuthBearer


def test_get_auth_bearer_with_token(auth_bearer_client: Client) -> None:
    """Bearer token 鉴权：Authorization: Bearer docs-token → 200。"""
    response = auth_bearer_client.send(GetAuthBearer())
    assert response.raw.status == 200, f"Bearer auth failed: {response.raw.text()}"


def test_get_auth_api_key_header(auth_apikey_header_client: Client) -> None:
    """API Key header 鉴权：X-API-Key: docs-key → 200。"""
    response = auth_apikey_header_client.send(GetAuthApiKeyHeader())
    assert response.raw.status == 200, f"API key header failed: {response.raw.text()}"


def test_get_auth_basic(auth_basic_client: Client) -> None:
    """Basic auth 鉴权：docs:docs → 200。"""
    response = auth_basic_client.send(GetAuthBasic())
    assert response.raw.status == 200, f"Basic auth failed: {response.raw.text()}"


def test_get_auth_api_key_query(auth_apikey_query_client: Client) -> None:
    """API Key query 鉴权：api_key=docs-query-key → 200。"""
    response = auth_apikey_query_client.send(GetAuthApiKeyQuery(api_key="docs-query-key"))
    assert response.raw.status == 200, f"API key query failed: {response.raw.text()}"
