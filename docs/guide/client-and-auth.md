# Client 与鉴权

## Client 是什么

`Client` 是 stoma 的运行时入口，负责持有 Playwright `APIRequestContext` 并发送 HTTP 请求。

`Client` 不直接创建 `APIRequestContext`，而是由用户在 `pw.request.new_context(...)` 中建好后注入。这种设计让 context 的生命周期完全由调用方控制。

构造方式见 `src/stoma/client.py:48-61`：

```python
ctx = pw.request.new_context(
    base_url="http://localhost:8000",
    extra_http_headers={"Authorization": "Bearer xxx"},
)
client = Client(context=ctx)

endpoint = GetUsers(limit=10)
response = client.send(endpoint)
# response: Response[T]，T 从 GetUsers 推断
```

stoma 是同步实现，async client 不在本版本。

## base_url 与全局 header

创建 Playwright `APIRequestContext` 时，可以传入一组常见参数控制全局行为：

```python
from playwright.sync_api import sync_playwright

pw = sync_playwright().start()
ctx = pw.request.new_context(
    base_url="https://api.example.com",
    extra_http_headers={"Authorization": "Bearer eyJhbGc..."},
)
client = Client(context=ctx)
```

`extra_http_headers` 会在所有请求上携带，等同于全局 header。如果某个请求需要覆盖某个 header，继续看下一节。

`new_context` 还支持 `storage_state`（用于 cookie / session 管理）和 `timeout` 等参数，详见 Playwright 官方文档。

## per-request header

APIRoute 中通过 `Annotated[str, Header()] + Field(serialization_alias=...)]` 标记的字段，会从请求头中提取参数值。在 `Client._execute_request` 中，这些字段会覆盖 `extra_http_headers` 中同名的全局 header。

`src/stoma/routing.py:88-102` 中 `_get_dependant` 的分类逻辑会将所有 `Header()` 标记的字段归入 `header_params` 列表，进而在请求构造时将 header 参数加入 `request.headers`。

`src/stoma/client.py:132-137` 中的 header 合并规则如下：

```python
# 合并 headers：自动派生的 Content-Type + APIRoute 的 headers（APIRoute 优先——允许覆盖自动 mime）。
derived_headers: dict[str, str] = {}
if request.body.raw_data and request.body.raw_data.media_type:
    derived_headers["Content-Type"] = request.body.raw_data.media_type
elif request.body.binary_file and request.body.binary_file.get("mimeType"):
    derived_headers["Content-Type"] = request.body.binary_file["mimeType"]
merged_headers: dict[str, str] = {**derived_headers, **(request.headers or {})}
```

`request.headers`（即 APIRoute 的 Header 字段）优先级高于自动派生的 `derived_headers`，从而实现 per-request 覆盖。

示例：假设 `extra_http_headers={"Authorization": "Bearer global-token"}`，但某个接口需要不同的 token：

```python
from typing import Annotated, ClassVar
from pydantic import Field
from stoma import Header, APIRoute, Client, JSONResponseSpec
from playwright.sync_api import sync_playwright


class GetUserById(APIRoute):
    """根据 ID 获取用户接口，动态传入 token。"""

    on_200: ClassVar[JSONResponseSpec] = JSONResponseSpec(200, "application/json", UserData)

    user_id: int
    authorization: Annotated[str, Header(), Field(serialization_alias="Authorization")]


pw = sync_playwright().start()
ctx = pw.request.new_context(
    base_url="https://api.example.com",
    extra_http_headers={"Authorization": "Bearer global-token"},
)
client = Client(context=ctx)

# 这个请求的 Authorization header 是 "Bearer per-request-token"，而非全局的 "Bearer global-token"
endpoint = GetUserById(user_id=42, authorization="Bearer per-request-token")
response = client.send(endpoint)
```

`serialization_alias="Authorization"` 确保字段名 `authorization` 在序列化时映射为 HTTP header 名称 `Authorization`。

## token / cookie / session

### token

token 通常通过 `extra_http_headers` 注入全局 `Authorization` header，或通过 per-request `Header()` 字段动态覆盖。

### cookie 与 session

stoma 不支持 `cookie` 参数。cookie 由 Playwright 的 `APIRequestContext` 管理。

在创建 context 时通过 `storage_state` 注入 cookie 或 session 状态：

```python
ctx = pw.request.new_context(
    base_url="https://api.example.com",
    storage_state="storage_state.json",  # Playwright 导出的登录状态
)
```

`storage_state` 可以是文件路径（字符串）或字典（包含 `cookies` 和 `origins` 列表）。Playwright 会自动在后续请求中携带对应的 cookie。stoma 只负责发送请求，cookie 的管理全部委托给 Playwright。

## dispose() 与生命周期

`Client.dispose()` 释放底层 Playwright `APIRequestContext`：

```python
class Client:
    def dispose(self) -> None:
        """释放 Playwright context。"""
        self._context.dispose()
```

推荐在以下时机调用：

**pytest fixture teardown：**

```python
@pytest.fixture
def client():
    pw = sync_playwright().start()
    ctx = pw.request.new_context(base_url="https://api.example.com")
    client = Client(context=ctx)
    yield client
    client.dispose()   # teardown 阶段释放
    pw.stop()
```

**with 上下文：**

```python
with sync_playwright() as pw:
    ctx = pw.request.new_context(base_url="https://api.example.com")
    client = Client(context=ctx)
    try:
        response = client.send(GetUsers())
    finally:
        client.dispose()
```

调用 `dispose()` 后，该 `Client` 实例不可继续使用。如需再次请求，需要重新创建 context 和 client。

[继续：stoma make](../codegen/stoma-make.md)
