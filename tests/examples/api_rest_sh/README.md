# api.rest.sh e2e 演示

本目录提供 stoma 框架对真实 HTTP API（api.rest.sh）的端到端演示。

## 目标

演示 stoma 从 OpenAPI spec 生成测试代码的完整流程，覆盖：

- codegen 代码生成（端到端验证，1 场景）
- 匿名端点 e2e 测试（7 个 happy-path 场景）

测试默认发往 https://api.rest.sh（真实网络请求），所有场景均基于 OpenAPI 3.1 spec（spec/api.rest.sh.json）驱动。

## 目录说明

| 路径 | 说明 |
|------|------|
| `spec/api.rest.sh.json` | OpenAPI 3.1 规范文件（约 169 KB），定义 api.rest.sh 所有端点、鉴权方案和响应 schema |
| `app/` | stoma make 生成的测试代码目录，包含 `models.py`（66 个 Pydantic 模型类）和 71 个 route 文件。**同时作为 e2e 测试的入口代码**，由 `test_codegen.py` 验证 `stoma make` 命令可用后供 `test_app.py` 直接 import 调用 |
| `conftest.py` | pytest fixtures：2 个 session 级 Client fixtures（匿名客户端） |
| `test_codegen.py` | codegen 验证测试（1 个），调用 ``stoma make`` 命令端到端验证生成流程 |
| `test_app.py` | 匿名端点 e2e 测试（7 个），发往 api.rest.sh 真实端点，所有场景均为 2xx happy-path |

## 运行命令

### 运行全部测试

```bash
pytest tests/examples/api_rest_sh/ -v
```

结果：8/8 pass（1 codegen + 7 e2e）

### 分别运行

```bash
# codegen 验证（1 test，不走网络）
pytest tests/examples/api_rest_sh/test_codegen.py -v

# 匿名 e2e（7 tests，走真实 api.rest.sh 网络）
pytest tests/examples/api_rest_sh/test_app.py -v
```

### 手动重新生成 app 代码

```bash
stoma make --spec tests/examples/api_rest_sh/spec/api.rest.sh.json \
           --out tests/examples/api_rest_sh/app
```

## 覆盖矩阵

### test_codegen.py（1 个）

`stoma make` 命令端到端验证，临时输出到 `tmp_path`（不修改仓库内 `app/`）：

| 断言 | 说明 |
|------|------|
| 退出码 0 | CLI 命令成功 |
| 无 `SCHEMA_UNSUPPORTED` 警告 | spec 中无 stoma 无法生成的端点 |
| `models.py` 生成 | OpenAPI 组件 schemas 解析成功 |
| 71 个 route 文件生成 | 与 spec 的 71 个 operation 一一对应 |
| 全部 ``.py`` 通过 ``ast.parse()`` | 生成的 Python 代码语法正确 |
| 至少 71 个文件含 ``from stoma import`` | 模板引用了 stoma 基类 |

### test_app.py（7 个 happy-path）

每个场景均为 2xx，刻意避开 stoma 框架已知 bug 边界：

| # | HTTP 方法 | 端点 | 请求体类型 | 响应类型 | Schema 校验 | 覆盖点 |
|---|-----------|------|------------|----------|-------------|--------|
| 1 | GET | /get | 无（+ query） | JSON | 是 | query 字符串拼接 |
| 2 | POST | /post | JSON raw | JSON | 是 | raw body 编码 |
| 3 | POST | /login | urlencoded form | JSON | 是 | form 编码 |
| 4 | DELETE | /books/123 | 无（+ path） | 204 No Content | 否 | path 插值 + 204 短路 |
| 5 | OPTIONS | /options | 无 | JSON | 是 | OPTIONS 回显 |
| 6 | GET | /bytes/100 | 无（+ path） | octet-stream | 否 | 非 JSON 响应字节读取 |
| 7 | GET | /image | 无 | image/* | 否 | Accept content-negotiation |

### 故意未覆盖的场景

以下测试场景涉及 stoma 框架的已知限制，**不纳入本示例**：

| # | 触发场景 | 框架限制 |
|---|----------|----------|
| 1 | 4xx 响应（如 ``/status/404``、``/anything/foo`` 真实不存在） | ``build_response`` 在 4xx 仍调 Pydantic schema 校验，可能抛 ``ValidationError`` |
| 2 | HEAD 响应（如 ``/head``） | HEAD 200 + 空 body 时框架仍尝试 ``api_response.body()``，可能抛错 |
| 3 | multipart/form-data 上传（``/uploads``） | spec 显式 ``requestBody.required=true`` 但 ``content: {}``，畸形 spec |
| 4 | PATCH/JSON Patch（``/books/{id}``） | 触发 #1 相同框架 bug（依赖 4xx 跳过 schema 校验） |
| 5 | ETag conditional headers（``/etag/{etag}``） | spec 缺 ``If-None-Match`` header 参数，无法做条件请求 |

上述 5 类限制的修复需要修改 `src/` 代码或 spec 文件，**不在本 examples 计划范围内**，建议作为后续 follow-up plan 处理。
