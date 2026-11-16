# 覆盖比对审计：`tests/examples/` 删除前的前置检查

**Purpose**: FR-019 要求删除 `tests/examples/`，但规格同时要求「删除后其回归能力不可因此丧失」。本文件是删除动作的**前置门禁记录**（对应 tasks.md T006）。

**审计时间**：2026-11-16
**审计方法**：逐项比对 `tests/examples/` 中将被删除的 13 个测试与 `tests/unit/` + `tests/integration/` 中现存覆盖。

---

## 结论

**无覆盖损失，可以删除。**

唯一的实质性差异是：**删除后将不再有针对第三方公开服务的网络级 e2e 测试**。但这**不构成覆盖损失** —— 原有的这类测试本身是**面向人的演示资产**，而非回归资产（依据见下），且其等价的本地化版本已存在。

---

## 依据一：这些示例测试从未进入 CI

`pyproject.toml` 的 pytest 配置：

```toml
[tool.pytest.ini_options]
addopts = "--ignore=tests/examples"
```

`tests/examples/` **被 pytest 配置显式排除**。`.github/workflows/release.yaml` 执行 `uv run pytest`，因此 CI 从来没有运行过这些示例。

> 结论：它们不是「回归资产」，而是「演示资产」。删除它们不会让 CI 的检测能力下降，因为 CI 从来没有依赖过它们。

## 依据二：现存集成测试用本地 mock 覆盖了等价能力

| 将被删除的测试 | 数量 | 等价覆盖 | 位置 |
|----------------|------|----------|------|
| `tests/examples/petstore/test_petstore.py` | 5 | `tests/integration/test_client.py` 的 `TestAPIRouteSend`（5 个）+ `TestEndToEndFlow` | 本地 FastAPI mock |
| `tests/examples/api_rest_sh/test_app.py` | 7 | `TestResponseEnvelope`（10 个）、`TestFormBody`、`TestScalarFormList`、`TestUploadFileBody`、`TestMixedFormAndFile`、`TestRawUploadBody` | 本地 FastAPI mock |
| `tests/examples/api_rest_sh/test_codegen.py` | 1 | `tests/integration/test_cli.py`（11 个，含 `test_codegen_all_methods`、`test_make_produces_working_models`、`test_models_equivalent_to_datamodel_codegen`） | 无网络 |

**具体的覆盖映射**：

| 原示例覆盖点 | 现存覆盖 |
|---------------|----------|
| path 参数插值 + schema 校验 | `TestAPIRouteSend.test_get_user_by_id`、`TestClient.test_send_extracts_path_params` |
| query 拼接 | `TestAPIRouteSend.test_get_users_list_with_params`、`TestClient.test_send_builds_query_params` |
| JSON body 编码 | `TestBodyMultipleParams`（5 个） |
| urlencoded form | `TestFormBody.test_form_urlencoded_login`、`TestScalarFormList` |
| multipart 上传 | `TestUploadFileBody`（2 个）、`TestMixedFormAndFile`、`TestOptionalUploadFile`（4 个） |
| octet-stream / 二进制 | `TestResponseEnvelope.test_binary_octet_stream`、`TestRawUploadBody`（6 个） |
| 204 No Content 短路 | `TestResponseEnvelope.test_204_no_content` |
| 非 JSON 响应 | `TestResponseEnvelope.test_text_plain`、`test_no_content_type_fallback` |
| 4xx 响应 | `TestExceptionHandling.test_returns_response_on_404` |
| 多 media type 警告 | `tests/integration/test_cli.py::test_make_collects_multi_media_type_warnings` |
| 生成产物可 import | `test_make_produces_working_models` |
| 全部 HTTP 方法 | `test_codegen_all_methods`、`TestAllMethodsSend`（HEAD/OPTIONS） |

## 依据三：现存测试数量与稳定性均优于原示例

| | 原示例（将删除） | 现存测试 |
|---|---|---|
| 测试数 | 13 | **438**（`tests/unit` + `tests/integration`） |
| 外部依赖 | petstore3.swagger.io、api.rest.sh（**已证实不稳定**：前者 4 个端点持续返回 500，后者规范与实际响应不一致） | 无（本地 mock） |
| CI 运行 | **否**（被 `--ignore` 排除） | 是 |

## 依据四：唯一的粒度差异

`tests/examples/api_rest_sh/test_codegen.py` 对 **71 个端点逐一断言**「文件已生成 + `ast.parse()` 通过 + 含 router import」。

现存 `tests/integration/test_cli.py::test_codegen_all_methods` 的端点数量较少。

**评估**：这是**规模级**而非**能力级**的差异 —— 它验证的是「同一份大规范能被完整生成」，而非「某种接口形态能否生成」（后者由各 `test_codegen_*` 覆盖）。且该测试依赖一份 169 KB 的第三方规范快照，本身属于演示资产。

**决策**：**不补齐**。理由：
1. 补齐意味着在主仓引入一份 169 KB 的第三方规范快照，与「删除示例目录、瘦身仓库」的目标相反。
2. 该能力可由 demo 仓库承担 —— demo 的 `make regen` + CI 漂移检测覆盖了「规范 → 生成 → 产物一致」的等价链路。
3. 端点形态覆盖（真正会出 bug 的地方）已由 `test_codegen_all_methods` 与各 `test_codegen_*` 覆盖。

**若后续发现需要**：可在 `tests/integration/fixtures/` 下放一份精简的自有规范（而非第三方快照），只覆盖多 media type、复合 schema 等边界形态。

---

## 回归门禁结果（T021）

删除 `tests/examples/` 后执行 `uv run pytest`：

```text
11 failed, 400 passed, 27 skipped
```

**这 11 个失败是 `master` 上既存的，与本特性无关。** 已用 stash 对照验证：把我的全部改动 stash 掉、在干净的 `master` 上运行，得到**完全相同的 11 个失败**。

失败的测试全部位于 `tests/unit/openapi/`：

| 文件 | 失败数 |
|------|--------|
| `tests/unit/openapi/test_parameters.py` | 3 |
| `tests/unit/openapi/test_renderer.py` | 8 |

**结论**：删除 `tests/examples/` **没有引入任何新的失败**，也没有减少通过的测试数（删除前 `master` 上是同样的 11 failed / 400 passed / 27 skipped）。回归门禁**通过**。

> 这 11 个既存失败属于 `src/stoma/openapi/` 的 codegen 问题，不在本特性范围内（规格明确排除产品功能变更）。建议单独提 issue 跟踪。

## 遗留事项

| # | 事项 | 状态 |
|---|------|------|
| 1 | 删除 `tests/examples/` | 待执行（T007） |
| 2 | 移除 `pyproject.toml` 的 `--ignore=tests/examples` | 待执行（T009） |
| 3 | 根 `tests/conftest.py` 的 docstring 提到 `tests/examples/petstore`、`tests/examples/api_rest_sh` | **需随删除更新**（见下） |
| 4 | `docs/guide/cli.md` 引用 `tests/examples/petstore/app` | 待改指 demo 仓（T011） |
| 5 | `README.md` 引用 `./tests/examples/petstore/` | 待改指 demo 仓（T029） |

### 遗留事项 3 的细节

`tests/conftest.py` 的模块 docstring 中：

```
子目录 ``tests/integration``、``tests/examples/petstore``、
``tests/examples/api_rest_sh`` 都不再各自定义 ``_shared_playwright``，
```

删除目录后该描述失准。**须同步更新** —— 这正是 G-2 门禁（文档字符串必须与代码匹配）的适用场景。

---

**审计结论**：覆盖比对通过，**可以执行删除**。遗留的文档同步事项已在 tasks.md 中分别对应 T009、T011、T029，以及本文件第 3 项（并入 T009 一并处理）。
