# 响应信封与数据校验

## 响应信封的结构

`Client.send()` 返回类型始终为 `Response[T]`，其中 `T` 由 endpoint 的类型参数决定。`Response` 是 dataclass，包含两个字段。

```python
from stoma import Response
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `raw` | `playwright.sync_api.APIResponse` | 原始 HTTP 响应，始终可用 |
| `expect` | `Callable[[ResponseSpec[T]], T]` | 按 spec 校验响应体并返回解析后的数据，类型为 `T` |

`raw` 始终可用，`expect` 方法需要传入对应的 `ResponseSpec` 才能返回校验后的数据。`BaseResponseSpec` 是响应协议的抽象基类，`JSONResponseSpec` 处理 JSON 响应，`RawResponseSpec[bytes]` 处理原始字节响应。

```python
from playwright.sync_api import sync_playwright as pw
from stoma import Client

with pw() as p:
    ctx = pw.request.new_context(base_url="https://api.example.com")
    client = Client(context=ctx)
    response = client.send(some_endpoint)

    # raw 始终可用
    print(response.raw.status)  # HTTP 状态码
    print(response.raw.headers)  # 响应头字典
    print(response.raw.body())  # 原始字节
```

## 校验流程：先发请求，再按需校验

v2 API 的设计原则是「先拿到响应，再按需校验」。调用方通过 `response.raw.status` 判断响应类型，然后决定是否需要校验以及使用哪个 spec 校验。

```python
response = client.send(endpoint)  # 不做任何校验，直接返回 Response

if response.raw.status == 200:
    data = response.expect(endpoint.on_200)  # 显式指定 spec 进行校验，类型为 T
elif response.raw.status == 404:
    error = response.expect(endpoint.on_404)  # 使用 404 对应的 spec 校验
```

这样做有几个好处：

1. **无隐式校验**：发送请求后不会自动校验，调用方完全掌控校验时机。
2. **状态码分离**：每个状态码有独立的 spec，调用方通过 `if response.raw.status == N` 明确分支。
3. **IDE 友好**：`response.expect(endpoint.on_200)` 的返回类型由 `endpoint.on_200` 的泛型决定，IDE 可自动联想。

## JSON 响应与 Pydantic 校验

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

    if response.raw.status == 200:
        user = response.expect(GetUsers().on_200)  # 类型为 UserData
        print(user.name)  # Pydantic 模型实例，IDE 可补全
```

### 错误路径

如果 JSON 解析成功但数据不符合 model 的定义，则抛出 `ValidationError`（stoma 的异常类，不是 pydantic 的）。`e.errors` 包含 Pydantic 校验错误的完整列表，格式为 `list[dict]`，每个 dict 包含 `loc`、`msg`、`type` 等键。

```python
from playwright.sync_api import sync_playwright as pw
from stoma import Client
from stoma.exceptions import ValidationError  # stoma 的 ValidationError，非 pydantic

with pw() as p:
    ctx = pw.request.new_context(base_url="https://api.example.com")
    client = Client(context=ctx)

    try:
        response = client.send(SomeEndpoint())
        if response.raw.status == 200:
            data = response.expect(SomeEndpoint().on_200)
    except ValidationError as e:
        print(e.message)  # 例如："响应数据校验失败: 1 validation error for UserData"
        for err in e.errors:
            print(err["loc"], err["msg"], err["type"])
```

## 非 JSON 响应（字节 / 文本）

使用 `RawResponseSpec[bytes]` 声明原始字节响应协议。`RawResponseSpec` 在 `BaseResponseSpec` 的基础上，直接返回 `response.body()` 的字节内容。

```python
from stoma.dependencies.response import RawResponseSpec

# 声明字节响应协议，适用于图片、PDF、zip 等二进制内容
spec = RawResponseSpec(status_code=200, media_type="image/png", target_type=bytes)

# 如果确定是纯文本响应，可用 str 类型
text_spec = RawResponseSpec(status_code=200, media_type="text/plain", target_type=str)
```

调用时，`response.expect(spec)` 直接返回 bytes 或 str：

```python
response = client.send(image_endpoint)

if response.raw.status == 200:
    raw_bytes = response.expect(image_endpoint.on_200)  # 类型为 bytes
    print(len(raw_bytes))
```

## 多状态码的处理

每个 endpoint 可以声明多个状态码的 spec，调用方通过 `response.raw.status` 判断后使用对应的 spec 校验：

```python
class GetBookById(APIRoute):
    @property
    def on_200(self) -> JSONResponseSpec[BookResponse]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=BookResponse)

    @property
    def on_404(self) -> JSONResponseSpec[ErrorResponse]:
        return JSONResponseSpec(status_code=404, media_type="application/json", model=ErrorResponse)

    book_id: int
```

```python
response = client.send(GetBookById(book_id=42))

if response.raw.status == 200:
    book = response.expect(GetBookById(book_id=42).on_200)  # BookResponse
elif response.raw.status == 404:
    error = response.expect(GetBookById(book_id=42).on_404)  # ErrorResponse
```

## 空响应与 204 短路

HTTP 204 No Content 或响应 body 为空时，`raw.body()` 返回空字节串 `b""`，不会抛出异常。

```python
response = client.send(delete_endpoint)

assert response.raw.status == 204
assert response.raw.body() == b""  # 安全调用，不会爆
```

框架在 `build_response` 内部对空 body 做了保护处理，即使服务器返回空 body 也不会触发 JSON 解析异常。

[继续：错误处理](./error-handling.md)
