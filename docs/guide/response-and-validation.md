# 响应信封与数据验证

## 响应信封的结构

`Client.send()` 返回类型始终为 `Response[T]`，其中 `T` 由 `APIRoute` 的泛型参数决定。`Response` 是 dataclass，包含两个字段。

```python
from stoma import Response
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `raw` | `playwright.sync_api.APIResponse` | 原始 HTTP 响应，始终可用 |
| `validated` | `T` | 由 `BaseResponseSpec.validate_response` 校验并解析后的响应数据，类型为 `T` |

`raw` 始终可用，`validated` 的类型由路由声明的响应协议决定。`BaseResponseSpec` 是响应协议的抽象基类，`JSONResponseSpec` 处理 JSON 响应，`RawResponseSpec[bytes]` 处理原始字节响应。

```python
from playwright.sync_api import sync_playwright as pw
from stoma import Client

with pw() as p:
    ctx = pw.request.new_context(base_url="https://api.example.com")
    client = Client(context=ctx)
    response = client.send(some_endpoint)

    # raw 始终可用
    print(response.raw.status)       # HTTP 状态码
    print(response.raw.headers)       # 响应头字典
    print(response.raw.body())        # 原始字节
```

## JSON 响应与 Pydantic 验证

使用 `JSONResponseSpec` 声明 JSON 响应协议。`JSONResponseSpec` 在 `BaseResponseSpec` 的基础上，通过 Pydantic `TypeAdapter` 按声明的 model 校验响应体，并返回强类型的 `T` 实例。

```python
from stoma.dependencies.response import JSONResponseSpec
from pydantic import BaseModel

class UserData(BaseModel):
    id: int
    name: str
    email: str

# 声明 JSON 响应协议
spec = JSONResponseSpec(status_code=200, media_type="application/json", model=UserData)
```

### Happy 路径

```python
from playwright.sync_api import sync_playwright as pw
from stoma import Client
from stoma.example.users import GetUsers  # OpenAPI 生成的 endpoint

with pw() as p:
    ctx = pw.request.new_context(base_url="https://api.example.com")
    client = Client(context=ctx)
    response = client.send(GetUsers())

    assert response.raw.status == 200
    user = response.validated  # 类型为 UserData
    print(user.name)  # Pydantic 模型实例，IDE 可补全
```

上述场景中，`validated` 被推断为 `UserData`（由 `GetUsers` 的返回类型决定），可直接访问 `.name` 等模型字段。

### 验证失败

如果 JSON 解析成功但数据不符合 model 的定义，则抛出 `ValidationError`（stoma 的异常类，不是 pydantic 的）。`e.errors` 包含 Pydantic 验证错误的完整列表，格式为 `list[dict]`，每个 dict 包含 `loc`、`msg`、`type` 等键。

```python
from playwright.sync_api import sync_playwright as pw
from stoma import Client
from stoma.exceptions import ValidationError  # stoma 的 ValidationError，非 pydantic

with pw() as p:
    ctx = pw.request.new_context(base_url="https://api.example.com")
    client = Client(context=ctx)

    try:
        response = client.send(SomeEndpoint())
        user = response.validated
    except ValidationError as e:
        print(e.message)  # 例如："响应数据验证失败: 1 validation error for UserData"
        for err in e.errors:
            print(err["loc"], err["msg"], err["type"])
```

## 非 JSON 响应（字节 / 文本）

使用 `RawResponseSpec[bytes]` 声明原始字节响应协议。`RawResponseSpec` 在 `BaseResponseSpec` 的基础上，直接返回 `response.body()` 的字节内容，不再是 `None`。

```python
from stoma.dependencies.response import RawResponseSpec

# 声明字节响应协议，适用于图片、PDF、zip 等二进制内容
spec = RawResponseSpec[bytes](status_code=200, media_type="image/png")

# 工厂方法更简洁
spec = RawResponseSpec.bytes(200, "application/octet-stream")
```

`response.validated` 即为字节内容，无需再做 `validated is None` 判断：

```python
response = client.send(image_endpoint)

# validated 直接就是 bytes
raw_bytes = response.validated  # 类型为 bytes
print(len(raw_bytes))
```

如果确定是纯文本响应，可用 `RawResponseSpec[str]`：

```python
spec = RawResponseSpec.text(200, "text/plain; charset=utf-8")

response = client.send(text_endpoint)
text = response.validated  # 类型为 str
print(text[:100])
```

## 错误状态码

框架对响应协议做严格校验。如果在 endpoint 中声明 `expect=route.on_200` 但服务端返回 400，`BaseResponseSpec.validate_response` 会先调用 `_assert_status` 做协议级校验，不匹配时直接抛 `AssertionError`。

```python
# 声明期望 200 状态码
spec = JSONResponseSpec(status_code=200, media_type="application/json", model=UserData)

response = client.send(SomeEndpoint())

# 如果服务端返回 400 而非 200，这里会抛 AssertionError
user = response.validated  # AssertionError: HTTP 状态码不匹配: 期望 200，实际为 400
```

`Client.send()` 在以下情况抛错：网络层失败（`HTTPError`）、JSON 解析失败（`ParseError`）、JSON 验证失败（`ValidationError`）、响应协议校验失败（`AssertionError`）。

对于 4xx 和 5xx 响应，如果 endpoint 没有声明严格的 `expect=` 校验，`send()` 仍会正常返回 `Response[T]`，调用方通过 `response.raw.status` 判断是否需要处理错误。

## 空响应与 204 短路

HTTP 204 No Content 或响应 body 为空时，`raw.body()` 返回空字节串 `b""`，不会抛出异常。

```python
response = client.send(delete_endpoint)

assert response.raw.status == 204
assert response.raw.body() == b""  # 安全调用，不会爆
```

框架在 `build_response` 内部对空 body 做了保护处理（见 `src/stoma/dependencies/response.py:88-94`），即使服务器返回空 body 也不会触发 JSON 解析异常。

[继续：错误处理](./error-handling.md)
