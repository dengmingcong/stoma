# api.rest.sh 端到端示例

本示例演示 stoma 框架对真实 HTTP API（api.rest.sh）的端到端能力，涵盖从 OpenAPI spec 到测试代码生成，再到实际请求发送的全流程。所有测试基于 OpenAPI 3.1 spec（spec/api.rest.sh.json）驱动，发往 https://api.rest.sh。生成的 `app/` 目录包含 66 个 Pydantic 模型类和 71 个 route 文件。完整说明见 [`tests/examples/api_rest_sh/README.md`](tests/examples/api_rest_sh/README.md)。

## 这个示例是什么

`tests/examples/api_rest_sh/` 提供两类测试：

- **codegen 验证**（1 个场景）：端到端验证 `stoma make` CLI 命令的可用性，确认生成的代码结构与语法符合预期。
- **匿名 e2e 测试**（7 个场景）：使用 stoma 生成的 route 类，对 api.rest.sh 的公开端点发送真实请求，覆盖 query、path、body、form、响应类型协商等常见 HTTP 交互模式。
  所有 7 个场景均为 2xx happy-path，刻意避开 stoma 框架已知 bug 的边界（4xx schema 校验、HEAD 空 body、畸形 multipart spec）。

运行 `pytest tests/examples/api_rest_sh/ -v` 可见 8/8 pass（1 个 codegen + 7 个 e2e）。

## 1 个 codegen 验证场景

`test_codegen.py` 通过 Typer `CliRunner` 直接调用 `stoma.cli:app`，临时输出到 `tmp_path`，不修改仓库内已有的 `app/` 目录。
本测试不依赖网络，仅验证本地 CLI 流水线。验证以下 5 项断言：

| 断言 | 说明 |
|------|------|
| 退出码 0 | `stoma make` CLI 命令成功完成 |
| 无 `SCHEMA_UNSUPPORTED` | spec 中所有端点均可被 stoma 解析，无不支持警告 |
| `models.py` 生成 | OpenAPI 组件 schemas 解析成功，生成 Pydantic 模型 |
| 71 个 route 文件生成 | 与 spec 中 71 个 operation 一一对应 |
| 全部 `.py` 通过 `ast.parse()` | 生成的 Python 代码语法正确，无 SyntaxError |
| 至少 71 个文件含 `from stoma import` | 模板引用了 stoma 基类 |

## 7 个 happy-path e2e 场景

每个场景均为 2xx 响应，刻意避开 stoma 框架已知 bug 的边界（4xx schema 校验、HEAD 空 body、畸形 multipart spec）。

| HTTP 方法 | 端点 | 请求体类型 | 响应类型 | 覆盖点 |
|-----------|------|------------|----------|--------|
| GET | /get | 无（+ query） | JSON | query 字符串拼接，schema 校验 |
| POST | /post | JSON raw | JSON | raw body 编码，schema 校验 |
| POST | /login | urlencoded form | JSON | form 编码，schema 校验 |
| DELETE | /books/123 | 无（+ path） | 204 No Content | path 插值，204 短路 |
| OPTIONS | /options | 无 | JSON | OPTIONS 回显，schema 校验 |
| GET | /bytes/100 | 无（+ path） | octet-stream | 非 JSON 响应字节读取 |
| GET | /image | 无 | image/* | Accept content-negotiation |

## 手动重新生成 + 已知限制

手动执行以下命令可重新生成 `app/` 目录：

```bash
stoma make --spec tests/examples/api_rest_sh/spec/api.rest.sh.json \
           --out tests/examples/api_rest_sh/app
```

以下 5 类场景涉及 stoma 框架已知限制，不在本示例覆盖范围内：

| 触发场景 | 框架限制 |
|----------|----------|
| 4xx 响应（如 `/status/404`） | `build_response` 在 4xx 仍调用 Pydantic schema 校验，可能抛 `ValidationError` |
| HEAD 响应（如 `/head`） | HEAD 200 + 空 body 时框架仍尝试 `api_response.body()`，可能抛错 |
| multipart/form-data 上传（如 `/uploads`） | spec 显式 `requestBody.required=true` 但 `content: {}`，畸形 spec 导致无法生成 |
| PATCH/JSON Patch（如 `/books/{id}`） | 触发与 4xx 相同的框架 bug（依赖 4xx 跳过 schema 校验） |
| ETag conditional headers（如 `/etag/{etag}`） | spec 缺 `If-None-Match` header 参数，无法做条件请求 |
