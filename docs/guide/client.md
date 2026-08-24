# Client

Stoma 定义的接口只存储数据，调用接口使用 `stoma.Client` 实现。

## 调用接口

Stoma 内部基于 Playwright [APIRequestContext](https://playwright.dev/python/docs/api/class-apirequestcontext) 实现接口调用，Stoma 不会对 `APIRequestContext` 做任何修改，所有特性都能正常使用。

`Client` 不直接创建 `APIRequestContext`，由用户建好后传入，由用户控制 Context 的声明周期，Stoma 会将接口的数据收集后发送给 `APIRequestContext`。

以调用接口 `GetUserByName` 为例。

```python
from playwright.sync_api import sync_playwright
from stoma import Client

with sync_playwright() as p:
    ctx = p.request.new_context(base_url="https://petstore3.swagger.io")
    client = Client(context=ctx)

    endpoint = GetUserByName(username="user1")
    response = client.send(endpoint)
    user = response.expect(endpoint.on_200)
    assert user.username == "user1"
```

实现过程：

1. 创建 `Client` 实例，传入事先创建的 `APIRequestContext` 实例。
2. 创建接口实例，确定接口参数的值。
3. 调用 `Client.send()`，传入接口实例。

### 响应

`Client.send()` 始终返回 [stoma.Response](../../src/stoma/dependencies/response.py) 实例。

`Response` 实例只有一个属性 `raw`，保存的是 `APIRequestContext` 接口请求函数的返回值，即 `playwright.sync_api.APIResponse`。

### 校验

`Response` 的 `expect()` 方法接受 [响应协议](./define-response-specs.md) 实例，可以临时创建一个响应协议，也可以使用接口已经绑定好的响应协议，示例中使用的是 property `on_200` 绑定的响应协议。

* 如果传入的是通用响应协议 `ResponseSpec`，Stoma 会校验响应的 `status_code`、`media_type`，并使用 `expected_type` 基于 `pydantic.TypeAdapter` 对响应体做校验并返回对应对象，示例中 `response.expect(endpoint.on_200)` 返回的就是 `User` 对象。
* 如果传入的是空响应协议 `EmptyResponseSpec`，Stoma 只会校验响应的 `status_code`，不返回任何值。

得益于泛型特性，IDE 能自动推断 `expect()` 的返回值类型，可以使用点自动联想该类型的属性。

![alt text](../assets/guide/quickstart/ide-autocomplete-response.png)

## 全局 Header 技巧

[创建 Playwright APIRequestContext](https://playwright.dev/python/docs/api/class-apirequest) 时，可以传入全局 Header 控制全局行为，比如传入认证后的 token 实现接口认证：

```python
ctx = p.request.new_context(
    base_url="https://api.example.com",
    extra_http_headers={"Authorization": "Bearer eyJhbGc..."},
)
client = Client(context=ctx)
```

`extra_http_headers` 会在所有请求上携带。


