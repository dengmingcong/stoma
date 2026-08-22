# stoma make

从 OpenAPI 规范文件自动生成接口测试代码。

## 命令概览

`stoma make` 读取 OpenAPI 规范文件（YAML 或 JSON），生成一份 `models.py`（由 `datamodel-code-generator` 产出 Pydantic 模型类）和每个 endpoint 对应一份 `route.py` 文件（引用 `models.py` 中的类型）。生成的代码依赖 stoma 运行时，可直接配合 Playwright 做接口测试。

完整运行示例见 `tests/examples/api_rest_sh/README.md`。

## `spec` 参数

位置参数，指定 OpenAPI 规范文件路径。

支持 OpenAPI 3.0 和 3.1，两者在 `src/stoma/openapi/version.py` 中定义为主版本字面量 `"3.0"` / `"3.1"`，分别对应 `openapi_pydantic` 的 v3_0 / v3_1 模型。解析时由 parser 根据 spec 根对象的 `openapi` 字段判断版本，注入对应版本的 Reference 类型供渲染器使用。

## `--out` / `-o`

指定输出目录路径，默认为当前目录（`Path(".")`）。

输出目录不存在时，CLI 自动创建：

```python
# src/stoma/cli.py:51-54
try:
    out.mkdir(parents=True, exist_ok=True)
except OSError as e:
    raise typer.BadParameter(f"无法创建输出目录: {out}") from e
```

若指定路径为文件而非目录，CLI 在尝试创建时抛出 `OSError`，最终以 `typer.BadParameter` 形式退出。

## `--no-format`

跳过生成后的 `ruff format` + `isort fix` 步骤。

默认情况下（未传 `--no-format`），`stoma make` 在生成 `models.py` 和每份 `route.py` 后，若系统 PATH 中存在 `ruff`，会自动调用以下两条命令：

```bash
ruff format <file>
ruff check --select I,F401 --fix <file>
```

传入 `--no-format` 时，`render_to_file` 和 `generate_models` 均跳过 ruff 调用，保持生成的代码原样输出。适用于以下场景：

- CI 流水线中已对输入 spec 做预处理，生成的代码不需要二次格式化。
- 需要保留生成代码的手写格式偏好，或在后续步骤中自行处理 import 顺序。

## 退出码与错误分级

`stoma make` 的错误分为三类，全部定义在 `src/stoma/openapi/renderer.py` 的 `GenerationErrorKind` 枚举中。CLI 在渲染完所有 endpoint 后，收集所有错误并按类别分组输出，最终只有特定类别导致非零退出码。

### `MULTI_MEDIA_TYPE` — 软警告

当某个 endpoint 的 `requestBody.content` 中存在多个 media type key 时触发。CLI 静默选用第一个 media type 并继续生成，输出警告但不记录为失败。

```text
⚠ 以下 endpoint 有多个 media type（已用第一个）：
  - GET /some/path
    endpoint 有多个 media type，已静默使用 'application/json'（其他被忽略：text/plain, application/xml）
```

此错误不导致非零退出码。

### `MISSING_RESPONSE_MODEL` — 软警告

当 endpoint 响应中引用的 Response 模型名在 `models.py` 中不存在时触发。CLI 跳过该 Response 类型的 import，改用 generic 响应类型，输出警告但不中断生成流程。

```text
⚠ 以下 endpoint 缺少 Response 模型（已用 generic）：
  - POST /books
    缺少 Response 模型 'BookResponse'（已跳过 import + generic）
```

此错误不导致非零退出码。

### `SCHEMA_UNSUPPORTED` — 硬错误

当 endpoint 的 spec 形态超出 stoma 当前实现支持范围时触发。例如 schema 含顶层 `oneOf` / `anyOf` / `allOf` 组合子（renderer 无法静态推断字段），或使用了无法映射到 Pydantic 模型的 schema 结构。此类 endpoint 跳过生成，不输出任何 route 文件。

```text
⚠ 以下 endpoint 生成失败（spec 不被支持）：
  - PUT /upload
    multipart/form-data request body schema with top-level oneOf/anyOf/allOf is not supported; use application/json with $ref + inline merge in the OpenAPI spec.
```

检测到任何 `SCHEMA_UNSUPPORTED` 错误时，CLI 调用 `raise typer.Exit(code=1)`，退出码为 1。

### 完整输出示例

```bash
$ stoma make --spec specs/001-generate-api/contracts/openapi.yaml --out src/example
⚠ 以下 endpoint 有多个 media type（已用第一个）：
  - GET /search
    endpoint 有多个 media type，已静默使用 'application/json'（其他被忽略：text/xml）
⚠ 以下 endpoint 缺少 Response 模型（已用 generic）：
  - DELETE /items/{id}
    缺少 Response 模型 'DeleteItemResponse'（已跳过 import + generic）
生成 models.py + 12 个 route 文件到 src/example:
  - get_books.py
  - create_book.py
  - get_book_by_id.py
  - update_book.py
  - delete_book.py
  - search.py
  - upload_file.py
  - get_health.py
  - post_login.py
  - get_items_.py
  - post_items_.py
  - get_users_me.py
```

若存在 `SCHEMA_UNSUPPORTED` 错误，输出末尾会追加对应警告块，CLI 以退出码 1 终止，不输出生成结果摘要。

## 响应声明格式

每个 endpoint 的 route 文件在类体内生成一组响应声明，格式为 `@property def on_<status>`：

```python
class GetBookById(APIRoute):
    @property
    def on_200(self) -> JSONResponseSpec[BookResponse]:
        return JSONResponseSpec(
            status_code=200,
            media_type="application/json",
            model=BookResponse,
        )

    @property
    def on_404(self) -> JSONResponseSpec[ErrorResponse]:
        return JSONResponseSpec(
            status_code=404,
            media_type="application/json",
            model=ErrorResponse,
        )
```

`on_<status>` 属性的命名规则如下：

- 精确状态码（如 `200`、`404`）→ `on_200`、`on_404`
- OpenAPI 通配符 → `on_default`、`on_4xx`、`on_5xx`（小写）
- 每个状态码生成一条独立的 `@property` 声明

渲染逻辑由 `EndpointRenderer._extract_response_specs`（`renderer.py` 第 836-960 行）实现，按 `status_code + media_type` 组合切分响应声明列表。

## 每个状态码一个 spec

stoma 采用"每个状态码一个 spec"的设计原则，原因如下：

**精确匹配语义**：`on_200` 只匹配 HTTP 200，不会误匹配其他状态码。这种设计避免了多状态码合并声明带来的隐式分支判断，调用方可精确断言每个状态码的响应结构。

**可独立校验**：调用方可以精确断言某个状态码的响应结构，例如：

```python
response = client.send(GetBookById(book_id=42))
if response.raw.status == 200:
    book = response.expect(GetBookById(book_id=42).on_200)  # BookResponse
elif response.raw.status == 404:
    error = response.expect(GetBookById(book_id=42).on_404)  # ErrorResponse
```

**多 media type 支持**：同一个状态码可能返回多种 media type（如 `application/json` 和 `application/problem+json`），此时渲染器生成两条独立的 spec：

```python
@property
def on_200(self) -> JSONResponseSpec[BookResponse]:
    return JSONResponseSpec(
        status_code=200,
        media_type="application/json",
        model=BookResponse,
    )


@property
def on_200_application_problem_plus_json(self) -> JSONResponseSpec[ErrorResponse]:
    return JSONResponseSpec(
        status_code=200,
        media_type="application/problem+json",
        model=ErrorResponse,
    )
```

`sanitize_media_type` 函数（`media_type.py` 第 100-127 行）负责将 media type 字符串转换为合法的 Python 属性名后缀。

**OpenAPI 通配符处理**：对于 `default`、`4XX`、`5XX` 等范围通配符，渲染器生成 `status_code=lambda s: ...` 形式的谓词：

- `default` → `status_code=lambda s: True`
- `4XX` → `status_code=lambda s: 400 <= s < 500`
- `5XX` → `status_code=lambda s: 500 <= s < 600`

[继续：代码生成规则](./generation-rules.md)
