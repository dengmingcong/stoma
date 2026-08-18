# 响应信封与数据验证

## 响应信封的结构

`Client.send()` 返回类型始终为 `Response[T]`，其中 `T` 由 `APIRoute` 的泛型参数决定。`Response` 是 dataclass，包含两个字段。

```python
from stoma import Response
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `raw` | `playwright.sync_api.APIResponse` | 原始 HTTP 响应，始终可用 |
| `validated` | `T \| None` | 仅当响应 content-type 为 JSON 时填充 Pydantic 模型实例 |

`raw` 始终可用，`validated` 仅 JSON 媒体类型时填充。其他 content-type（如图片、PDF、纯文本）下 `validated` 为 `None`，调用方通过 `raw` 字段获取原始内容。

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

当响应的 content-type 为 JSON 时，`build_response` 会自动把响应体解析为 Python 对象，再通过 `T` 对应的 Pydantic 模型验证，结果存入 `validated` 字段。验证通过后，`validated` 的类型为 `T`（即 Pydantic 模型实例），而非 `list[dict]` 等原始类型。

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
    assert isinstance(response.validated, list)
    print(response.validated[0].name)  # Pydantic 模型实例，IDE 可补全
```

上述场景中，`validated` 被推断为 `list[UserData]`（由 `GetUsers` 的返回类型决定），可直接访问 `.name` 等模型字段。

### 验证失败

如果 JSON 解析成功但数据不符合 `T` 的定义，则抛出 `ValidationError`（stoma 的异常类，不是 pydantic 的）。`e.errors` 包含 Pydantic 验证错误的完整列表，格式为 `list[dict]`，每个 dict 包含 `loc`、`msg`、`type` 等键。

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

如果响应的 content-type 不是 JSON，`validated` 为 `None`，响应体需要自行解析。

`APIResponse` 提供两个原生方法：

- `response.raw.body()` — 返回 `bytes`，适用于图片、PDF、zip 等二进制内容
- `response.raw.text()` — 返回解码后的字符串，适用于纯文本响应

参考 `src/stoma/dependencies/response.py:88-126` 的实现逻辑：非 JSON 响应会跳过 JSON 解析路径，直接返回 `Response(raw=api_response, validated=None)`。

```python
response = client.send(some_binary_endpoint)

if response.validated is None:
    # 非 JSON content-type，走 raw 路径
    raw_bytes = response.raw.body()
    print(len(raw_bytes))

    # 如果你确定是纯文本
    text = response.raw.text()
    print(text[:100])
```

## 错误状态码

**4xx / 5xx 不抛错。** 框架不根据 HTTP 状态码自动抛出异常，所有错误由调用方自行判断。

`Client.send()` 仅在以下情况抛错：网络层失败（`HTTPError`）、JSON 解析失败（`ParseError`）、JSON 验证失败（`ValidationError`）。对于 4xx 和 5xx 响应，请求本身成功送达服务器，`send()` 正常返回 `Response[T]`，调用方通过 `response.raw.status` 判断是否需要处理错误。

参考 `src/stoma/client.py:71-95` 的实现：请求执行和响应构建均在 try 块内完成，捕获的异常不包含 HTTP 状态码错误。

推荐模式：

```python
response = client.send(some_endpoint)

if response.raw.status != 200:
    handle_error(response.raw.status, response.raw.body())
    return

# 正常流程
data = response.validated
```

## 空响应与 204 短路

HTTP 204 No Content 或响应 body 为空时，`validated` 为 `None`，`raw.body()` 返回空字节串 `b""`，不会抛出异常。

```python
response = client.send(delete_endpoint)

assert response.raw.status == 204
assert response.validated is None
assert response.raw.body() == b""  # 安全调用，不会爆
```

框架在 `build_response` 内部对空 body 做了保护处理（见 `src/stoma/dependencies/response.py:88-94`），即使服务器返回空 body 也不会触发 JSON 解析异常。

[继续：错误处理](./error-handling.md)
