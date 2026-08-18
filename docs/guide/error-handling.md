# 异常处理

本文档介绍 stoma 框架抛出的各类异常，以及推荐的错误处理模式。

关于 4xx 响应不抛错的设计原则，详见[响应与验证](./response-and-validation.md)。

## 异常一览

框架定义了四个顶层异常，全部继承自 `StomaError`：

| 异常 | 父类 | 抛出条件 | 典型 cause | 何时不要捕获 |
|------|------|----------|------------|-------------|
| `HTTPError` | `StomaError` | HTTP 请求无法发送、超时，或 `_execute_request` 抛出未处理异常 | 网络不可达、DNS 解析失败、连接超时 | 只在需要区分网络错误与业务逻辑错误时捕获 |
| `ParseError` | `StomaError` | 响应 body 为 JSON 但无法解析 | 服务器返回了畸形 JSON、响应 content-type 声明为 JSON 但 body 实际不是 | 非 JSON 响应路径不需要捕获 |
| `ValidationError` | `StomaError` | JSON 解析成功但 Pydantic 模型验证失败 | 响应字段类型不匹配、缺少必填字段、字段值超出枚举范围 | 只在需要处理验证失败逻辑时捕获，框架默认已打印详细错误 |
| `OpenAPISchemaError` | `StomaError` | `stoma make` 生成阶段 OpenAPI schema 校验失败 | schema 缺少路径、media type 配置错误、schema 语法错误 | CLI 生成阶段，框架已自行处理 |

## HTTPError

`HTTPError` 在网络层发生问题时抛出，常见原因包括：网络不可达、DNS 解析失败、连接超时。

框架在 `Client.send` 中会把所有未处理的异常包装为 `HTTPError`，并保留原始异常作为 `cause`。

### 最小示例

```python
from playwright.sync_api import sync_playwright as pw
from stoma import Client
from stoma.exceptions import HTTPError

with pw() as p:
    ctx = p.request.new_context(base_url="https://httpbin.org")
    client = Client(context=ctx)

    try:
        result = client.send(endpoint)  # endpoint = GetUsers()
    except HTTPError as e:
        print(f"HTTP 请求失败: {e.message}")
        if e.status_code is not None:
            print(f"状态码: {e.status_code}")
        print(f"响应: {e.response_text}")
```

### 常见错误修复

超时错误通常由目标服务繁忙或网络链路不稳定导致：

```python
# ❌ 错误：不做任何处理，直接崩溃
result = client.send(endpoint)

# ✅ 修复：捕获 HTTPError 并区分是否需要重试
try:
    result = client.send(endpoint)
except HTTPError as e:
    if e.status_code == 503:
        print("服务暂时不可用，建议稍后重试")
    else:
        raise
```

## ParseError

`ParseError` 在响应 body 无法解析为 JSON 时抛出，可通过 `response_text` 属性查看原始响应内容。

此异常发生在框架尝试调用 `response.json()` 之后，表明服务器返回的内容与 content-type 声明不一致。

### 最小示例

```python
from playwright.sync_api import sync_playwright as pw
from stoma import Client
from stoma.exceptions import ParseError

with pw() as p:
    ctx = p.request.new_context(base_url="https://httpbin.org")
    client = Client(context=ctx)

    try:
        result = client.send(endpoint)  # endpoint = GetUsers()
    except ParseError as e:
        print(f"响应解析失败: {e.message}")
        print(f"原始响应: {e.response_text}")
```

### 常见错误修复

服务器返回了非 JSON 内容但声明了 JSON content-type：

```python
# ❌ 错误：不区分异常类型，全部用 ValidationError 处理
try:
    result = client.send(endpoint)
except ValidationError as e:
    print(e.errors)

# ✅ 修复：先捕获 ParseError，检查原始响应内容
try:
    result = client.send(endpoint)
except ParseError as e:
    print(f"无法解析 JSON: {e.response_text}")
    # 可能是服务器返回了 HTML 错误页或其他文本内容
except ValidationError as e:
    print(f"数据验证失败: {e.errors}")
```

## ValidationError

`ValidationError` 在 JSON 解析成功后、Pydantic 模型验证失败时抛出。

与 `pydantic.ValidationError` 不同，`stoma.exceptions.ValidationError` 是框架的公共异常类型，`errors` 字段直接暴露 Pydantic 验证错误详情列表。

### 最小示例

```python
from playwright.sync_api import sync_playwright as pw
from stoma import Client
from stoma.exceptions import ValidationError

with pw() as p:
    ctx = p.request.new_context(base_url="https://httpbin.org")
    client = Client(context=ctx)

    try:
        result = client.send(endpoint)  # endpoint = GetUsers()
    except ValidationError as e:
        print(f"验证失败: {e.message}")
        for err in e.errors or []:
            print(f"  字段: {err.get('loc')}, 原因: {err.get('msg')}")
```

### 常见错误修复

常见原因是接口契约变更但测试代码未同步更新：

```python
# ❌ 错误：用 broad-catch 吞掉所有异常，掩盖真正原因
try:
    result = client.send(endpoint)
except Exception:
    pass

# ✅ 修复：明确捕获 ValidationError 并打印结构化错误
try:
    result = client.send(endpoint)
except ValidationError as e:
    print("接口契约可能已变更:")
    for err in e.errors or []:
        print(f"  路径: {'.'.join(str(l) for l in err.get('loc', []))}")
        print(f"  原因: {err.get('msg')}")
        print(f"  类型: {err.get('type')}")
```

## 推荐写法

### 组合模式

推荐在外层捕获 `HTTPError`（覆盖网络层和超时错误），在内层捕获 `ValidationError`（处理响应数据验证问题）。`ParseError` 可根据业务需求决定是否单独处理。

```python
from playwright.sync_api import sync_playwright as pw
from stoma import Client
from stoma.exceptions import HTTPError, ParseError, ValidationError

with pw() as p:
    ctx = p.request.new_context(base_url="https://httpbin.org")
    client = Client(context=ctx)

    try:
        result = client.send(endpoint)  # endpoint = GetUsers()
        # ValidationError 在此处抛出，表示响应数据验证失败
    except HTTPError as e:
        # 外层捕获：网络层错误、超时、所有非验证异常
        print(f"HTTP 请求失败 [{e.status_code}]: {e.message}")
        if e.response_text:
            print(f"响应内容: {e.response_text[:200]}")
        raise
    except ParseError as e:
        # 中间层捕获：响应体不是合法 JSON
        print(f"响应解析失败: {e.message}")
        print(f"原始内容: {e.response_text[:200] if e.response_text else ''}")
        raise
    except ValidationError as e:
        # 内层捕获：响应数据不符合 Pydantic 模型定义
        print(f"响应数据验证失败:")
        for err in e.errors or []:
            print(f"  字段 {'.'.join(str(l) for l in err.get('loc', []))}: {err.get('msg')}")
        raise
```

### 反模式

不要在外层 broad-catch `Exception`。这会掩盖框架内部的编程错误，使调试变得困难：

```python
# ❌ 反模式：捕获所有异常，可能吞掉框架内部错误
try:
    result = client.send(endpoint)
except Exception as e:
    print(f"请求失败: {e}")

# ✅ 正解：明确列出需要处理的异常类型
try:
    result = client.send(endpoint)
except HTTPError:
    raise
except ValidationError:
    raise
```

关于 4xx 响应的处理逻辑，详见[响应与验证](./response-and-validation.md)。
