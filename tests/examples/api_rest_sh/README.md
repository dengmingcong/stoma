# api.rest.sh e2e 演示

本目录提供 stoma 框架对真实 HTTP API（api.rest.sh）的端到端演示。

## 目标

演示 stoma 从 OpenAPI spec 生成测试代码的完整流程，覆盖：

- codegen 代码生成（静态验证）
- 匿名端点 e2e 测试（13 场景）
- 鉴权端点 e2e 测试（4 场景，支持 Basic / Bearer / API Key header / API Key query）

测试默认发往 https://api.rest.sh（真实网络请求），所有场景均基于 OpenAPI 3.1 spec（spec/api.rest.sh.json）驱动。

## 目录说明

| 路径 | 说明 |
|------|------|
| `spec/api.rest.sh.json` | OpenAPI 3.1 规范文件（约 169 KB），定义 api.rest.sh 所有端点、鉴权方案和响应 schema |
| `app/` | stoma make 生成的测试代码目录，包含 `models.py`（66 个 Pydantic 模型类）和 71 个 route 文件 |
| `conftest.py` | pytest fixtures：6 个 session 级 Client fixtures，分别对应无鉴权、Basic、Bearer、API Key header、API Key query 场景 |
| `test_codegen.py` | codegen 验证测试（3 个），不依赖网络，验证生成代码结构和语法 |
| `test_e2e_anon.py` | 匿名端点 e2e 测试（13 个），发往 api.rest.sh 真实端点 |
| `test_e2e_auth.py` | 鉴权端点 e2e 测试（4 个），分别验证 4 种鉴权方案 |

## 运行命令

### 生成代码

```bash
stoma make --spec tests/examples/api_rest_sh/spec/api.rest.sh.json \
           --out tests/examples/api_rest_sh/app
```

### 运行全部测试

```bash
pytest tests/examples/api_rest_sh/ -v
```

结果：17/20 pass（3 fail 来自 stoma runtime 限制，见已知限制）

### 分别运行

```bash
# codegen 验证（3 tests，不走网络）
pytest tests/examples/api_rest_sh/test_codegen.py -v

# 匿名 e2e（13 tests，10 pass / 3 fail）
pytest tests/examples/api_rest_sh/test_e2e_anon.py -v

# 鉴权 e2e（4 tests，全部 pass）
pytest tests/examples/api_rest_sh/test_e2e_auth.py -v
```

## 覆盖矩阵

### HTTP 方法与场景覆盖

| HTTP 方法 | 端点 | 参数 | Body 类型 | 响应类型 | Auth 方案 | 测试文件 |
|-----------|------|------|-----------|----------|-----------|----------|
| GET | /get | status (query) | JSON | JSON | 无 | test_e2e_anon.py |
| GET | /anything/{path} | path (path) | JSON | JSON | 无 | test_e2e_anon.py |
| POST | /post | 无 | JSON | JSON | 无 | test_e2e_anon.py |
| POST | /login | username (form) | form | JSON | 无 | test_e2e_anon.py |
| POST | /uploads | file (multipart) | multipart/form-data | JSON | 无 | test_e2e_anon.py |
| PATCH | /books/{book-id} | book_id (path) | JSON Patch | JSON | 无 | test_e2e_anon.py |
| DELETE | /books/{book-id} | book_id (path) | 无 | 无 | 无 | test_e2e_anon.py |
| HEAD | /head | 无 | 无 | 无 | 无 | test_e2e_anon.py |
| OPTIONS | /options | 无 | 无 | JSON | 无 | test_e2e_anon.py |
| GET | /bytes/{n} | n (path) | 无 | octet-stream | 无 | test_e2e_anon.py |
| GET | /image | 无 | 无 | image/* | 无 | test_e2e_anon.py |
| GET | /status/{code} | code (path) | 无 | JSON | 无 | test_e2e_anon.py |
| GET | /etag/{etag} | etag (path) | 无 | JSON | 无 | test_e2e_anon.py |
| GET | /auth/bearer | 无 | 无 | JSON | Bearer | test_e2e_auth.py |
| GET | /auth/api-key-header | 无 | 无 | JSON | API Key (header) | test_e2e_auth.py |
| GET | /auth/basic | 无 | 无 | JSON | Basic | test_e2e_auth.py |
| GET | /auth/api-key-query | api_key (query) | 无 | JSON | API Key (query) | test_e2e_auth.py |

### 默认鉴权凭证

api.rest.sh 在 x-cli-config 段声明以下默认值，测试直接使用：

| Auth 方案 | 字段 | 默认值 |
|-----------|------|--------|
| Basic | username:password | `docs:docs` |
| Bearer | token | `docs-token` |
| API Key (header) | X-API-Key | `docs-key` |
| API Key (query) | api_key | `docs-query-key` |

### 已知限制

| # | 测试 | 失败原因 | 修复方向 |
|---|------|----------|----------|
| 1 | test_get_anything_path | api.rest.sh 返回 404（resource 不存在）+ stoma 未对 4xx 响应跳过 schema 校验，导致 ValidationError | 修改 `src/dependencies/response.py` 在 4xx/5xx 时跳过 schema 校验 |
| 2 | test_post_upload_spec_malformed | spec 畸形（`requestBody.required=true` 但 `content: {}`） + stoma 未对 4xx 跳过校验 | 修改 spec 显式声明 `multipart/form-data` schema + stoma 4xx 跳过校验 |
| 3 | test_head_method | HEAD 200 + 空 body，stoma 仍调 `api_response.json()` 导致 JSONDecodeError | 修改 `src/dependencies/response.py` 对 HEAD/空 body 情况跳过 JSON 解析 |

以上 3 个失败需要修改 `src/` 代码或 spec 文件，**不在本 examples 计划范围内**，建议作为后续 follow-up plan 处理。
