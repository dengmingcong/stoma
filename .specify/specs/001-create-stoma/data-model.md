# 数据模型

## 核心实体

### RouteMeta
- 字段：`method: str`、`path: str`。
- 关系：`APIRoute._route_meta` 为 ClassVar，生成时由装饰器注入。
- 规则：不可变（Pydantic `ConfigDict(frozen=True)`）；与用户字段命名隔离。

### APIRoute[T]
- 字段：Pydantic BaseModel 字段即请求参数；`_route_meta: RouteMeta`（ClassVar）。
- 行为：`send` 方法封装 HTTP 调用，收集实例字段→构造请求→解析响应为 `T`（当前版本同步实现，异步支持后续迭代）。
- 状态转移：实例创建→调用→返回响应模型或抛出校验异常。

### 参数标记（Query/Path/Header/Body）
- 作用：用于 Annotated 元信息，标注参数来源、默认值、校验约束与别名。
- 关系：与 APIRoute 字段联合，驱动请求构造（query/path/header/body 分拣）。

### 请求模型（Request Models）
- 来源：从 OpenAPI `requestBody` 和非路径参数推导；继承 Pydantic BaseModel。
- 规则：字段包含类型、默认值、校验（ge/le/regex 等），可选性由 OpenAPI required 推导。

### 响应模型（Response Models）
- 来源：OpenAPI responses 中的 2xx schema；生成 Pydantic 模型或内联类型别名。
- 规则：APIRoute 泛型参数引用此模型，`send` 将 JSON 解析并校验。

### APIRouter（装饰器命名空间）
- 方法：`get/post/put/patch/delete(path)` → 返回类装饰器。
- 规则：装饰器需验证被装饰类继承 APIRoute，并写入 `_route_meta`。

### CLI 命令
- `stoma make --spec <openapi> --out <dir> --feature <name>`
- 输入：OpenAPI yaml/json 文件路径、输出目录、feature 名称。
- 输出：按 routing/models/params/templates 分层的 Python 代码与路由/模型文件。
