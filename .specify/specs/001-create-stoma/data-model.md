# 数据模型

## 核心实体

### Dependant
- 字段：`method: str`、`path: str`、`path_params: list[ModelField]`、`query_params: list[ModelField]`、`header_params: list[ModelField]`、`body_params: list[ModelField]`。
- 关系：`APIRoute._dependant` 为 ClassVar，装饰器调用 `_get_dependant()` 时生成并缓存。
- 规则：不可变（`@dataclass(frozen=True)`）；与用户字段命名隔离；包含完整的路由元数据和参数依赖分析结果。

### ModelField
- 字段：`name: str`、`alias: str`、`field_info: FieldInfo`、`param: Param | None`。
- 作用：表示一个字段的完整信息，用于 Dependant 中存储参数字段。
- 规则：不可变（`@dataclass(frozen=True)`）。

### APIRoute[T]
- 字段：Pydantic BaseModel 字段即请求参数；`_dependant: Dependant | None`（ClassVar）。
- 行为：`send` 方法封装 HTTP 调用，收集实例字段→构造请求→解析响应为 `T`（当前版本同步实现，异步支持后续迭代）；`_get_dependant()` 类方法用于获取/生成参数依赖定义。
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
- 规则：装饰器调用被装饰类的 `_get_dependant(method, path)` 方法生成并缓存元数据和参数依赖。

### CLI 命令
- `stoma make --spec <openapi> --out <dir> --feature <name>`
- 输入：OpenAPI yaml/json 文件路径、输出目录、feature 名称。
- 输出：按 routing/models/params/templates 分层的 Python 代码与路由/模型文件。
