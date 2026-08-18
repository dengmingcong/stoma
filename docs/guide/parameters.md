# 参数标记

接口测试需要声明每个参数的来源（path、query、header、body、form、file）。stoma 通过 `Annotated[T, Mark()]` 风格将标记与类型绑定，由框架完成请求的序列化与发送。

## 参数标记总览

`Path()`、`Query()`、`Header()`、`Body()`、`Form()`、`UploadFile` 六种标记分别对应 HTTP 请求的不同位置。所有标记都是静默元数据，仅用于告知框架「这个字段应该从哪里取值」，不影响 Pydantic 的校验行为。

### 本质：`Annotated[T, Mark()]`

参数标记采用 PEP 593 的 `Annotated` 语法，将类型 `T` 与标记对象配对：

```python
from typing import Annotated
from stoma import Path, Query

user_id: Annotated[int, Path()]
limit: Annotated[int, Query()] = 20
```

标记对象本身不存储值，只描述值的来源。实际取值由类属性默认值提供，或在构造 endpoint 实例时传入。

### 自动类型推断

当字段没有任何显式标记时，stoma 会根据字段类型自动归类。归类逻辑在 `src/stoma/routing.py:69-87` 中实现，规则如下：

| 类型条件 | 自动归类 | 说明 |
|----------|----------|------|
| 字段 alias 匹配路径 `{placeholder}` | Path | 路径占位符自动捕获 |
| `int / str / bool / float` 等标量类型 | Query | 查询参数 |
| `BaseModel` 子类、`dict`、`list`、`dataclass` | Body | 请求体（自动 JSON 序列化） |
| `UploadFile` / `list[UploadFile]` | 文件 Body | multipart/form-data 或原始字节 |

只要添加任意显式标记，就会跳过自动推断，完全由标记决定归属。

## Path / Query / Header

三个标记分别对应 URL 路径参数、查询字符串、HTTP 请求头。

### Path

路径参数用于 URL 中的占位符。字段名或 alias 必须与路径模板中的 `{placeholder}` 完全一致：

```python
from typing import Annotated
from stoma import APIRoute, APIRouter, Path

router = APIRouter()


@router.get("/users/{user_id}")
class GetUserById(APIRoute[dict]):
    """根据 ID 获取用户。"""

    user_id: Annotated[int, Path()]
```

无显式标记时，如果字段名出现在路径占位符中，也会自动归类为 Path。但显式写 `Path()` 更清晰，且可以附加 Pydantic `Field()` 约束（如 `ge=1`）。

### Query

查询参数附加在 URL 后面（`?limit=10&offset=0`）。无显式标记时，所有标量字段默认归入 Query：

```python
from typing import Annotated
from stoma import APIRoute, APIRouter, Query

router = APIRouter()


@router.get("/users")
class GetUsers(APIRoute[list[dict]]):
    """获取用户列表，支持分页。"""

    limit: Annotated[int, Query()] = 20
    offset: Annotated[int, Query()] = 0
```

默认值直接写在类属性右侧，不需要在 `Annotated` 中额外处理。

### Header

请求头参数从 HTTP 请求头中提取。常见场景是传递认证令牌：

```python
from typing import Annotated
from stoma import APIRoute, APIRouter, Header

router = APIRouter()


@router.get("/users")
class GetUsers(APIRoute[list[dict]]):
    """获取用户列表，需要认证。"""

    authorization: Annotated[str, Header()] = "Bearer token"
```

`Header()` 默认使用字段名作为请求头名称（不区分大小写，HTTP 协议会自动处理）。如果需要使用其他请求头名称，可以用 `Field(serialization_alias="X-Custom-Header")` 覆盖。

## Body

Body 标记用于声明请求体参数。请求体会被 JSON 序列化后放入 HTTP 请求体。

### 显式标记与自动归类

BaseModel 子类作为字段类型时，即使不加 `Body()` 也会被自动归类为 body：

```python
from typing import Annotated
from pydantic import BaseModel
from stoma import APIRoute, APIRouter, Body


class UserCreateRequest(BaseModel):
    name: str
    email: str


router = APIRouter()


@router.post("/users")
class CreateUser(APIRoute[dict]):
    """创建用户。"""

    body: Annotated[UserCreateRequest, Body()]
```

显式写 `Body()` 的意义在于可以控制 `embed` 和 `media_type` 两个进阶开关。

### embed=True：嵌入单个字段

当只有一个 body 字段且 `embed=True` 时，请求体会被包成 `{"field": value}` 的形式，而不是直接把值放在 body 根部：

```python
from typing import Annotated
from pydantic import BaseModel
from stoma import APIRoute, APIRouter, Body


class UserCreateRequest(BaseModel):
    name: str
    email: str


router = APIRouter()


@router.post("/users")
class CreateUser(APIRoute[dict]):
    """创建用户，embed=True 将整个请求体嵌入到 {"body": ...} 下。"""

    body: Annotated[UserCreateRequest, Body(embed=True)]
```

发送的请求体为 `{"body": {"name": "...", "email": "..."}}`，而不是直接在根部展开字段。

`embed=False`（默认）是更常见的做法，直接把 BaseModel 展开为顶层 JSON 对象。

### media_type="text/plain"

当同时满足以下三个条件时，`media_type` 才会生效：

1. 只有 1 个 body 参数
2. `embed=False`
3. 字段类型是标量（而非 BaseModel）

这种情况下，请求体会以纯文本形式发送，Content-Type 头被设置为指定的值：

```python
from typing import Annotated
from stoma import APIRoute, APIRouter, Body

router = APIRouter()


@router.post("/text-body")
class SendText(APIRoute[dict]):
    """发送纯文本请求体。"""

    content: Annotated[str, Body(media_type="text/plain")] = ""
```

如果任意条件不满足，`media_type` 参数会被静默忽略。

## Form

Form 标记用于发送 `application/x-www-form-urlencoded` 或 `multipart/form-data`（无文件时）格式的表单数据。

### 基本用法

`Form()` 接受标量类型或标量列表：

```python
from typing import Annotated
from stoma import APIRoute, APIRouter, Form

router = APIRouter()


@router.post("/login")
class Login(APIRoute[dict]):
    """用户登录，支持标签。"""

    username: Annotated[str, Form()]
    tags: Annotated[list[str], Form()] = []
```

标量字段发送时作为单个值，`list[str]` 字段发送时同一个 key 会重复出现多次，对应 FastAPI 服务端解析为 `list`。

### 与 Body / UploadFile 互斥

Form 字段与 Body 字段、UploadFile 字段不能共存于同一个 endpoint。`src/stoma/routing.py:184-185` 在构建路由元数据时会检查此约束：

```python
# 错误示例：Form + Body 混用会抛出 ValueError
class BadEndpoint(APIRoute[dict]):
    # 错误：Body 与 Form 不可混用
    body: Annotated[dict, Body()]   # Body 与 Form 互斥
    username: Annotated[str, Form()]  # 正确做法：去掉 Body，把 dict 字段改为 Form
```

如果需要同时发送表单字段和文件，应使用 UploadFile（见下一节），stoma 会自动以 multipart 形式发送。

## UploadFile

UploadFile 用于声明文件上传字段，携带本地文件路径。

### 基本用法

`UploadFile(path=pathlib.Path(...))` 传入本地文件路径，框架会读取文件内容并发送到服务器：

```python
import pathlib
from stoma import APIRoute, APIRouter, UploadFile

router = APIRouter()


@router.post("/upload")
class UploadAvatar(APIRoute[dict]):
    """上传用户头像。"""

    avatar: UploadFile
```

stoma 会自动以 `multipart/form-data` 形式发送，Content-Type 根据文件扩展名自动设置为 `image/png`、`text/plain` 等。

### 显式 multipart

如果表单字段与文件字段共存，整个请求会以 multipart 形式发送：

```python
import pathlib
from typing import Annotated
from stoma import APIRoute, APIRouter, Form, UploadFile

router = APIRouter()


@router.post("/upload-mix")
class UploadWithForm(APIRoute[dict]):
    """同时发送表单字段和文件。"""

    username: Annotated[str, Form()]
    avatar: UploadFile
```

`Form()` 标量字段会被序列化为 FormData 的文本字段，UploadFile 序列化为文件字段，整体走 multipart 编码。

### upload_as_multipart=False

如果端点声明了 `upload_as_multipart=False`，整个请求 body 会被替换为文件的原始字节内容，而不是 multipart 编码：

```python
import pathlib
from stoma import APIRoute, APIRouter, UploadFile

router = APIRouter()


@router.post("/raw-upload", upload_as_multipart=False)
class RawUpload(APIRoute[dict]):
    """裸字节上传。"""

    file: UploadFile
```

此时 Content-Type 由文件的 mimetype 自动决定，或者可以通过显式的 `Header(serialization_alias="Content-Type")` 覆盖。

`upload_as_multipart=False` 有以下约束：body 必须恰好包含一个 UploadFile 字段，且不能有任何 Form 字段或 Body 字段。

## 进阶开关

三个进阶开关分别控制请求体的打包方式、编码格式、发送形式。以下是选择策略表：

| 场景 | embed | media_type | upload_as_multipart | 说明 |
|------|-------|------------|---------------------|------|
| BaseModel 请求体，默认 | `False`（默认） | `None`（默认） | `True`（默认） | 直接展开为 JSON 对象 |
| BaseModel 请求体，需要包一层 key | `True` | `None` | `True` | 发送 `{"body": {...}}` |
| 纯文本请求体（如 legacy 接口） | `False` | `"text/plain"` | `True` | 仅标量字段生效 |
| 单文件裸字节上传 | `False` | `None` | `False` | 整条 body 是文件字节 |
| 表单字段加文件混合 | 不适用 | 不适用 | `True`（默认） | multipart 自动组合 |

当不确定用哪个时，优先用默认值（所有开关都不写）。只有在明确知道接口需要特定格式时，才按需打开对应开关。

## 常见错误

### 1. Path 字段名与 `{placeholder}` 不一致

```python
# 错误：路径占 {user_id}，字段名却是 userId
class GetUserById(APIRoute[dict]):
    userId: Annotated[int, Path()]  # userId ≠ user_id
```

修复建议：字段名或 alias 必须与路径占位符完全匹配，本例中应改为 `user_id`。

### 2. Form + Body 混用

```python
# 错误：同一 endpoint 中同时存在 Body 和 Form
class BadEndpoint(APIRoute[dict]):
    body: Annotated[dict, Body()]
    username: Annotated[str, Form()]
```

修复建议：Body 与 Form 互斥，只能选一种。如果需要文件上传，用 UploadFile 替代 Body。

### 3. UploadFile + Body 混用

```python
# 错误：同时存在 Body 和 UploadFile
class BadUpload(APIRoute[dict]):
    metadata: Annotated[dict, Body()]
    file: UploadFile
```

修复建议：UploadFile 本身就是 body 的一种表示，去掉 Body 字段，或将 Body 内容合并到 UploadFile 所在的 BaseModel 中。

### 4. 多 body 字段时误用 embed

```python
# 错误：两个 body 字段时 embed=True 不生效
class BadMultiBody(APIRoute[dict]):
    name: Annotated[str, Body(embed=True)]
    email: Annotated[str, Body()]  # 多 body 时 embed 会被忽略
```

修复建议：多 body 字段时 `embed` 参数会被静默忽略，每个字段按 alias 独立嵌入到顶层 JSON。如果需要特定包装结构，在 BaseModel 定义时处理好层级。

### 5. scalar 类型使用了 Body(media_type)

```python
# 错误：标量 + embed=True 时 media_type 不会生效
class BadTextBody(APIRoute[dict]):
    content: Annotated[str, Body(embed=True, media_type="text/plain")]
```

修复建议：`media_type` 仅在同时满足「仅 1 个 body 参数 + embed=False + 标量字段」三个条件时生效。本例中应去掉 `embed=True`。

---

以上涵盖了六种参数标记的用法、自动推断规则、进阶开关以及典型错误。响应体的校验方式见下一文档。

[继续：响应与校验](./response-and-validation.md)
