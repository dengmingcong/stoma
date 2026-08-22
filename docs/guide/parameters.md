# 参数标记

HTTP 接口由多个部分组成，Stoma 通过 `Annotated[T, Mark()]` 风格声明参数。

Stoma 定义了 `Path()`、`Query()`、`Header()`、`Body()`、`Form()`、`UploadFile` 六种标记，分别对应 HTTP 请求的不同位置。

```info
`Path()`、`Query()`、`Header()`、`Body()`、`Form()` 实际是函数，返回的是同名数据类型的实例，`UploadFile` 是一种类型。
```

## Path()

`Path()` 用于声明路径参数，用于替换路径中的占位符。

```python
from typing import Annotated
from stoma import APIRoute, APIRouter, JSONResponseSpec, Path

router = APIRouter()


@router.get("/users/{user_id}")
class GetUserById(APIRoute):
    """根据 ID 获取用户。"""

    user_id: Annotated[int, Path()]

    @property
    def on_200(self) -> JSONResponseSpec[dict]:
        return JSONResponseSpec(
            200,
            media_type="application/json",
            model=dict,
        )
```

`Client` 发送请求之前，会使用字段 `user_id` 的值替换路径中的占位符。


## Query()

`Query()` 用于声明查询参数。

```python
from typing import Annotated
from stoma import APIRoute, APIRouter, JSONResponseSpec, Query

router = APIRouter()


@router.get("/users")
class GetUsers(APIRoute):
    """获取用户列表，支持分页。"""

    limit: Annotated[int, Query()] = 20
    offset: Annotated[int, Query()] = 0

    @property
    def on_200(self) -> JSONResponseSpec[list[dict]]:
        return JSONResponseSpec(
            200,
            media_type="application/json",
            model=list[dict],
        )
```

`Client` 发送请求之前，会将查询参数附加在 URL 后面（`?limit=20&offset=0`）。


## Header()

`Header()` 用于声明请求头参数，常见场景是传递认证令牌。

```python
from typing import Annotated
from pydantic import Field
from stoma import APIRoute, APIRouter, Header, JSONResponseSpec

router = APIRouter()


@router.get("/users")
class GetUsers(APIRoute):
    """获取用户列表，需要认证。"""

    authorization: Annotated[str, Header(), Field(serialization_alias="Authorization")] = "Bearer token"

    @property
    def on_200(self) -> JSONResponseSpec[list[dict]]:
        return JSONResponseSpec(
            200,
            media_type="application/json",
            model=list[dict],
        )
```

`Client()` 发送请求之前会将请求头传递给 Playwright（`{"Authorization": "Bearer token"}`）。


## Body()

`Body()` 标记用于声明请求体参数。

单个 Body 参数和多个 Body 参数的处理有差异。

### 单个 Body 参数

单个 Body 参数可能是 Pydantic 模型，也可能是标量（`str`、`int` 等），处理方式也有差异。

#### Pydantic 模型

```python
from typing import Annotated
from pydantic import BaseModel
from stoma import APIRoute, APIRouter, Body, JSONResponseSpec


class UserCreateRequest(BaseModel):
    name: str
    email: str


router = APIRouter()


@router.post("/users")
class CreateUser(APIRoute):
    """创建用户。"""

    body: Annotated[UserCreateRequest, Body()]

    @property
    def on_201(self) -> JSONResponseSpec[dict]:
        return JSONResponseSpec(
            201,
            media_type="application/json",
            model=dict,
        )
```

只有一个 Body 参数且参数类型是 Pydantic 模型时，Stoma 会忽略字段名，只将模型的字段传给 Playwright：

```json
{
    "name": "...", 
    "email": "..."
}
```

如果想要将模型字段包裹在字段名中，需设置 `embed=True`。

```python
@router.post("/users")
class CreateUser(APIRoute):
    """创建用户。"""

    body: Annotated[UserCreateRequest, Body(embed=True)]

    @property
    def on_201(self) -> JSONResponseSpec[dict]:
        return JSONResponseSpec(status_code=201, media_type="application/json", model=dict)
```

这样 Stoma 传给 Playwright 时会嵌套字段名：

```json
{
    "body": {
        "name": "...", 
        "email": "..."
    }
}
```

#### 标量

```python
from typing import Annotated
from stoma import APIRoute, APIRouter, Body, JSONResponseSpec

router = APIRouter()


@router.post("/text-body")
class SendText(APIRoute):
    """发送纯文本请求体。"""

    content: Annotated[str, Body()] = "some text"

    @property
    def on_201(self) -> JSONResponseSpec[dict]:
        return JSONResponseSpec(status_code=201, media_type="application/json", model=dict)
```

只有一个 Body 参数且参数类型是标量时，Stoma 也会忽略字段名，只将字段的值传给 Playwright：

```
some text
```

请求头中的 Content-Type 由 Playwright 确定，如果想要指定 Content-Type，可以通过设置 `media_type` 实现。

```python
@router.post("/text-body")
class SendText(APIRoute):
    """发送纯文本请求体。"""

    content: Annotated[str, Body(media_type="text/plain")] = "some text"

    @property
    def on_201(self) -> JSONResponseSpec[dict]:
        return JSONResponseSpec(status_code=201, media_type="application/json", model=dict)
```

这种情况下，Content-Type 头被设置为 `text/plain`。

如果想要将字段名也传给 Playwright，需要设置 `embed=True`。

```python
@router.post("/text-body")
class SendText(APIRoute):
    """发送纯文本请求体。"""

    content: Annotated[str, Body(embed=True)] = "some text"

    @property
    def on_201(self) -> JSONResponseSpec[dict]:
        return JSONResponseSpec(status_code=201, media_type="application/json", model=dict)
```

这样 Stoma 会传给 Playwright：

```json
{
    "content": "some text"
}
```

注意，此时 `media_type` 不再生效，因为 Content-Type 会被确定为 `application/json`。

所以，只有同时满足以下三个条件，`media_type` 才会生效：

1. 只有 1 个 Body 参数。
2. `embed=False`。
3. 字段类型是标量。

### 多个 Body 参数

```python
from typing import Annotated
from pydantic import BaseModel
from stoma import APIRoute, APIRouter, Body, JSONResponseSpec


class UserCreateRequest(BaseModel):
    name: str
    email: str


router = APIRouter()


@router.post("/users")
class CreateUser(APIRoute):
    """创建用户。"""

    data: Annotated[UserCreateRequest, Body()]
    phone: Annotated[str, Body()]

    @property
    def on_201(self) -> JSONResponseSpec[dict]:
        return JSONResponseSpec(status_code=201, media_type="application/json", model=dict)
```

存在多个 Body 参数时，Stoma 会忽略 `embed` 和 `media_type`，始终以 dict 形式传递给 Playwright，将字段名作为 key。

```json
{
    "data": {
        "name": "...", 
        "email": "..."
    }, 
    "phone": "..."
}
```

## Form()

`Form()` 标记用于声明表单数据，只能与标量类型或标量列表一起使用。

```python
from typing import Annotated
from stoma import APIRoute, APIRouter, Form, JSONResponseSpec

router = APIRouter()


@router.post("/login")
class Login(APIRoute):
    """用户登录，支持标签。"""

    username: Annotated[str, Form()]
    tags: Annotated[list[str], Form()] = []

    @property
    def on_201(self) -> JSONResponseSpec[dict]:
        return JSONResponseSpec(status_code=201, media_type="application/json", model=dict)
```

Stoma 会将 `Form()` 字段的值填充到 Playwright [FormData](https://playwright.dev/python/docs/api/class-formdata) 实例，并最终赋值给 [APIRequestContext.fetch()](https://playwright.dev/python/docs/api/class-apirequestcontext#api-request-context-fetch) 方法的 `form=` 参数，Playwright 会自动设置 `Content-Type` 请求头为 `application/x-www-form-urlencoded`。

对于标量列表，会调用 `FormData` 的 `append()` 方法添加表单数据。


## UploadFile

UploadFile 用于声明文件上传字段。

```python
from stoma import APIRoute, APIRouter, JSONResponseSpec, UploadFile

router = APIRouter()


@router.post("/upload")
class UploadAvatar(APIRoute):
    """上传用户头像。"""

    avatar: UploadFile

    @property
    def on_201(self) -> JSONResponseSpec[dict]:
        return JSONResponseSpec(status_code=201, media_type="application/json", model=dict)
```

`UploadFile` 目前只有一个参数 `path`，类型为 `pathlib.Path`，用于指定本地文件路径，Stoma 会将 `path` 的值填充到 Playwright [FormData](https://playwright.dev/python/docs/api/class-formdata) 实例，并最终赋值给 [APIRequestContext.fetch()](https://playwright.dev/python/docs/api/class-apirequestcontext#api-request-context-fetch) 方法的 `multipart=` 参数，Playwright 会自动推断文件名并将 `Content-Type` 请求头设置为 `multipart/form-data`。

## Form() + UploadFile

`Form()` 字段可以和 `UploadFile` 字段一起使用，Stoma 会将填充后的 [FormData](https://playwright.dev/python/docs/api/class-formdata) 实例赋值给 [APIRequestContext.fetch()](https://playwright.dev/python/docs/api/class-apirequestcontext#api-request-context-fetch) 方法的 `multipart=` 参数，Playwright 会将 `Content-Type` 请求头设置为 `multipart/form-data`。

```python
import pathlib
from typing import Annotated
from stoma import APIRoute, APIRouter, Form, JSONResponseSpec, UploadFile

router = APIRouter()


@router.post("/upload-mix")
class UploadWithForm(APIRoute):
    """同时发送表单字段和文件。"""

    username: Annotated[str, Form()]
    avatar: UploadFile

    @property
    def on_201(self) -> JSONResponseSpec[dict]:
        return JSONResponseSpec(status_code=201, media_type="application/json", model=dict)
```

⚠️ 注意：存在 `Form()` 或 `UploadFile` 参数时，不能存在 `Body()` 参数。

### Postman binary Body

从前面的示例可以看出，只要存在 `UploadFile` 字段，Stoma 都会将请求头设置为 `multipart/form-data`，但是 OpenAPI 支持上传单个文件时将请求头 `Content-Type` 设置为上传文件的 [Media type](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/MIME_types)，可以参考 Postman 中类型为 binary 的 Body（单文件上传）。

Stoma 使用 `upload_as_multipart=False` 支持这种情况，请求体会被替换为文件的原始字节内容（而不是 multipart 编码），并将请求头 `Content-Type` 设置为上传文件的 Media type。

```python
import pathlib

from stoma import APIRoute, APIRouter, JSONResponseSpec, UploadFile

router = APIRouter()


@router.post("/raw-upload", upload_as_multipart=False)
class RawUpload(APIRoute):
    """裸字节上传。"""

    file: UploadFile

    @property
    def on_201(self) -> JSONResponseSpec[dict]:
        return JSONResponseSpec(status_code=201, media_type="application/json", model=dict)
```

`upload_as_multipart=False` 只在这种情况下生效：

* body 只包含一个 `UploadFile` 字段，且没有其他 `Form()` 字段。

## 省略标记

`Path()`、`Query()`、`Header()`、`Body()` 标记可以省略。

以路径参数为例，省略 `Path()` 标记时，如果字段名和路径占位符一致，会被自动识别为路径参数。

```python
@router.get("/users/{user_id}")
class GetUserById(APIRoute):
    """根据 ID 获取用户。"""

    user_id: int

    @property
    def on_200(self) -> JSONResponseSpec[dict]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=dict)
```

如果有别名，需要别名和路径占位符一致。

```python
@router.get("/users/{userId}")
class GetUserById(APIRoute):
    """根据 ID 获取用户。"""

    user_id: Annotated[int, Field(serialization_alias="userId")]

    @property
    def on_200(self) -> JSONResponseSpec[dict]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=dict)
```

注意：不管什么类型的参数，有别名时就只会用别名对比，没有别名才会使用字段名。后面用参数名表示别名和字段名的竞争结果。

多种类型参数省略标记时，识别顺序如下：

1. 参数名和路径占位符一致，则识别为路径参数。
2. 判断类型是否是复合类型，如果是复合类型，则识别为请求体参数。
3. 非复合类型（标量）识别为查询参数。
