# Petstore e2e 演示

本目录提供 stoma 框架对官方 Swagger Petstore 的端到端演示，演示从 OpenAPI 3.0 规范到生成代码到实际 HTTP 请求的完整链路。

## 目标

演示 stoma 从 OpenAPI 3.0 spec（Petstore v1.0.27）生成接口测试代码并调用真实公开 Petstore 服务的完整流程，覆盖：

- stoma make 命令生成测试代码（app/ 目录）
- 8 个 happy-path e2e 场景（全部 2xx，无 body 或 JSON body 类型）

测试默认发往 https://petstore3.swagger.io/api/v3（真实网络请求），所有场景均基于 OpenAPI 3.0.4 spec（spec/openapi.json）驱动。

## 目录说明

| 路径 | 说明 |
|------|------|
| `spec/openapi.json` | OpenAPI 3.0.4 规范文件（约 17 KB），定义 Petstore 所有端点、鉴权方案和响应 schema |
| `app/` | stoma make 生成的测试代码目录，包含 `models.py`（Pydantic 模型类）和 18 个 route 文件。**同时作为 e2e 测试的入口代码**，由 conftest.py 提供 session 级 Client fixture，供 `test_app.py` 直接 import 调用 |
| `conftest.py` | pytest fixtures：1 个 session 级 Client fixture（匿名客户端，发往 petstore3.swagger.io） |
| `test_app.py` | 匿名端点 e2e 测试（8 个），发往真实 Petstore 端点；当前 2 个 PASS（scenario 3、8），6 个 xfail（见"已知限制"） |

## 运行命令

### 运行全部测试

```bash
pytest tests/examples/petstore/test_app.py -v
```

结果：2 passed, 6 xfailed（当前 2/8 场景 PASS，其余 6 个 xfail 原因见"已知限制"）

### 手动重新生成 app 代码

```bash
stoma make --spec tests/examples/petstore/spec/openapi.json \
           --out tests/examples/petstore/app
```

## 覆盖矩阵

### test_app.py（8 个 happy-path）

每个场景均为 2xx，刻意避开 stoma 框架已知 bug 边界：

| # | HTTP 方法 | 端点 | 请求体类型 | 响应类型 | Schema 校验 | 覆盖点 |
|---|-----------|------|------------|----------|-------------|--------|
| 1 | GET | /store/inventory | 无 | JSON | 是 | query 字符串拼接 + schema 校验 |
| 2 | POST | /store/order | JSON | JSON | 是 | raw body 编码 + schema 校验 |
| 3 | GET | /store/order/{orderId} | 无 | JSON | 是 | path 插值 + schema 校验 |
| 4 | DELETE | /store/order/{orderId} | 无 | 200 | 否 | path 插值 + DELETE 语义 |
| 5 | POST | /user/createWithList | JSON array | JSON | 是 | array body 编码 + schema 校验 |
| 6 | GET | /user/login | query | 字符串 | 否 | query 拼接 + 非 schema 响应 |
| 7 | GET | /user/logout | 无 | 200 | 否 | 无副作用 e2e 调用 |
| 8 | GET | /user/{username} | 无 | JSON | 是 | path 插值 + schema 校验 |

### 故意未覆盖的场景

以下测试场景涉及 stoma 框架的已知限制，**不纳入本示例**：

| # | 触发场景 | 框架限制 |
|---|----------|----------|
| 1 | OAuth2 鉴权端点（pet 组 /pet/{petId}/uploadImage） | stoma 不处理 OAuth2 鉴权流程 |
| 2 | octet-stream 二进制上传（/pet/{petId}/uploadImage） | octet-stream body 类型为已知限制 |
| 3 | POST /user（application/xml） | XML body 编码不在本示例范围内 |

## 已知限制

### 为什么 6 个场景 xfail

当前测试结果为 2 passed, 6 xfailed，原因分为两类：

**petstore3 服务器问题（4 个）：**
- GET /store/inventory — 服务器返回 500
- POST /store/order — 服务器返回 500
- POST /user/createWithList — 服务器返回 500
- DELETE /store/order/{orderId=1} — order_id=1 不存在（服务器 404，非 stoma 问题）

**stoma ParseError on string body（2 个）：**
- GET /user/login — 响应 Content-Type 为 application/json，但 body 是裸字符串（如 "Logged in user session: 6219368480151290063"），不是合法 JSON 字符串字面量，stoma json.loads() 失败触发 ParseError
- GET /user/logout — 同上，响应 Content-Type 为 application/json，但 body 是裸字符串（如 "User logged out"），不是合法 JSON 字符串字面量，stoma json.loads() 失败触发 ParseError

### 其他已知限制

- 不覆盖 OAuth2 鉴权端点（pet 组），stoma 目前不处理 OAuth2 流程
- 不覆盖 octet-stream 二进制上传（uploadFile），已知限制
- 不写 test_codegen.py，Petstore 仅作 e2e 演示
- 公共服务 petstore3.swagger.io 偶发 5xx，建议本地起 mock server 替代

上述限制的修复需要修改 `src/` 代码，**不在本 examples 计划范围内**，建议作为后续 follow-up plan 处理。
