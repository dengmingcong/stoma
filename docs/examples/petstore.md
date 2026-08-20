# Swagger Petstore 端到端示例

本示例演示 stoma 框架对官方 Swagger Petstore（OpenAPI 3.0.4）的端到端能力，覆盖从 OpenAPI spec 到测试代码生成再到实际 HTTP 请求的完整链路。所有测试发往 https://petstore3.swagger.io/api/v3，生成的 `app/` 目录包含 18 个 route 文件。完整说明见 [`tests/examples/petstore/README.md`](../tests/examples/petstore/README.md)。

## 这个示例是什么

`tests/examples/petstore/` 提供 8 个匿名端点 e2e 场景，刻意避开 stoma 框架已知 bug 边界（OAuth2、octet-stream、XML body）。

当前测试结果：2 passed, 6 xfailed。6 个 xfail 中，4 个源于 petstore3 服务器返回 500，2 个源于 stoma 对 application/json content-type 但 body 为裸字符串触发 ParseError。

不写 `test_codegen.py`，Petstore 仅作 e2e 演示。

## 8 个 happy-path e2e 场景

| HTTP 方法 | 端点 | 请求体类型 | 响应类型 | Schema 校验 | 覆盖点 | 当前状态 |
|-----------|------|------------|----------|-------------|--------|----------|
| GET | /store/inventory | 无 | JSON | 是 | query 字符串拼接 + schema 校验 | xfail（服务器 500） |
| POST | /store/order | JSON | JSON | 是 | raw body 编码 + schema 校验 | xfail（服务器 500） |
| GET | /store/order/{orderId} | 无 | JSON | 是 | path 插值 + schema 校验 | PASS（orderId=2） |
| DELETE | /store/order/{orderId} | 无 | 200 | 否 | path 插值 + DELETE 语义 | xfail（orderId=1 不存在） |
| POST | /user/createWithList | JSON array | JSON | 是 | array body 编码 + schema 校验 | xfail（服务器 500） |
| GET | /user/login | query | 字符串 | 否 | query 拼接 + 非 schema 响应 | xfail（stoma ParseError） |
| GET | /user/logout | 无 | 200 | 否 | 无副作用 e2e 调用 | xfail（stoma ParseError） |
| GET | /user/{username} | 无 | JSON | 是 | path 插值 + schema 校验 | PASS |

## 手动重新生成 + 已知限制

手动执行以下命令可重新生成 `app/` 目录：

```bash
stoma make --spec tests/examples/petstore/spec/openapi.json \
           --out tests/examples/petstore/app
```

以下 4 类场景涉及 stoma 框架已知限制，不在本示例覆盖范围内：

| 触发场景 | 框架限制 |
|----------|----------|
| OAuth2 鉴权端点（pet 组 /pet/{petId}/uploadImage） | stoma 不处理 OAuth2 鉴权流程 |
| octet-stream 二进制上传（/pet/{petId}/uploadImage） | octet-stream body 类型为已知限制 |
| POST /user（application/xml） | XML body 编码不在本示例范围内 |
| GET /user/login、/user/logout（裸字符串 body） | stoma 对 application/json content-type 但 body 为裸字符串触发 ParseError |

上述限制的修复需要修改 `src/` 代码，**不在本 examples 计划范围内**。
