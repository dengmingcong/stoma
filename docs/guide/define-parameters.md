# Parameters

<!-- README-I18N:START -->

<p align="center">
  <b>English</b> ·
  <a href="./define-parameters.zh.md">中文</a>
</p>

<!-- README-I18N:END -->
Stoma declares parameters in the `Annotated[T, Mark()]` style.

Stoma defines six parameter marks — `Path()`, `Query()`, `Header()`, `Body()`, `Form()` and `UploadFile` — each corresponding to a different position in an HTTP request.

```info
`Path()`, `Query()`, `Header()`, `Body()` and `Form()` are functions that return an instance of the data type of the same name; `UploadFile` is a type.
```
## Path()

`Path()` declares a path parameter, used to replace a placeholder in the path.

```python
@router.get("/users/{user_id}")
class GetUserById(APIRoute):
    """Get a user by ID."""

    user_id: Annotated[int, Path()]
```

Before `Client` sends the request, it replaces the placeholder in the path with the value of the field `user_id`.

## Query()

`Query()` declares a query parameter.

```python
@router.get("/users")
class GetUsers(APIRoute):
    """Get a list of users, with pagination."""

    limit: Annotated[int, Query()] = 20
    offset: Annotated[int, Query()] = 0
```

Before `Client` sends the request, it appends the query parameters to the URL (`?limit=20&offset=0`).

## Header()

`Header()` declares a request header parameter — a common way to pass an auth token.

```python
@router.get("/users")
class GetUsers(APIRoute):
    """Get a list of users, requires authentication."""

    authorization: Annotated[str, Header(), Field(serialization_alias="Authorization")] = "Bearer token"
```

Before `Client()` sends the request, it passes the headers to Playwright (`{"Authorization": "Bearer token"}`).

## Body()

The `Body()` mark declares a request body parameter.

A single body parameter and multiple body parameters are handled differently.

### A single body parameter

A single body parameter may be a Pydantic model or a scalar (`str`, `int`, and so on), and the two are handled differently.

#### Pydantic model

```python
from typing import Annotated
from pydantic import BaseModel
from stoma import APIRoute, APIRouter, Body, ResponseSpec

class UserCreateRequest(BaseModel):
    name: str
    email: str

router = APIRouter()

@router.post("/users")
class CreateUser(APIRoute):
    """Create a user."""

    body: Annotated[UserCreateRequest, Body()]
```

When there is exactly one body parameter and its type is a Pydantic model, Stoma ignores the field name and passes only the model's fields to Playwright:

```json
{
    "name": "...",
    "email": "..."
}
```

To wrap the model's fields in the field name instead, set `embed=True`.

```python
@router.post("/users")
class CreateUser(APIRoute):
    """Create a user."""

    body: Annotated[UserCreateRequest, Body(embed=True)]
```

Now Stoma nests the field name when it passes the body to Playwright:

```json
{
    "body": {
        "name": "...",
        "email": "..."
    }
}
```

#### Scalar

```python
from typing import Annotated
from stoma import APIRoute, APIRouter, Body, ResponseSpec

router = APIRouter()

@router.post("/text-body")
class SendText(APIRoute):
    """Send a plain text request body."""

    content: Annotated[str, Body()] = "some text"
```

When there is exactly one body parameter and its type is a scalar, Stoma ignores the field name too and passes only the field's value to Playwright:

```
some text
```

Playwright decides the `Content-Type` header. To set it yourself, use `media_type`.

```python
@router.post("/text-body")
class SendText(APIRoute):
    """Send a plain text request body."""

    content: Annotated[str, Body(media_type="text/plain")] = "some text"
```

In this case the `Content-Type` header is set to `text/plain`.

To pass the field name to Playwright as well, set `embed=True`.

```python
@router.post("/text-body")
class SendText(APIRoute):
    """Send a plain text request body."""

    content: Annotated[str, Body(embed=True)] = "some text"
```

Now Stoma passes this to Playwright:

```json
{
    "content": "some text"
}
```

Note that `media_type` no longer takes effect here, because the `Content-Type` is determined to be `application/json`.

So `media_type` only takes effect when all three of these conditions hold:

1. There is exactly 1 body parameter.
2. `embed=False`.
3. The field type is a scalar.

### Multiple body parameters

```python
from typing import Annotated
from pydantic import BaseModel
from stoma import APIRoute, APIRouter, Body, ResponseSpec

class UserCreateRequest(BaseModel):
    name: str
    email: str

router = APIRouter()

@router.post("/users")
class CreateUser(APIRoute):
    """Create a user."""

    data: Annotated[UserCreateRequest, Body()]
    phone: Annotated[str, Body()]
```

When there are multiple body parameters, Stoma ignores `embed` and `media_type` and always passes a dict to Playwright, using the field names as keys.

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

The `Form()` mark declares form data, and can only be used with scalar types or lists of scalars.

```python
from typing import Annotated
from stoma import APIRoute, APIRouter, Form, ResponseSpec

router = APIRouter()

@router.post("/login")
class Login(APIRoute):
    """Log in a user, supports tags."""

    username: Annotated[str, Form()]
    tags: Annotated[list[str], Form()] = []
```

Stoma fills the values of the `Form()` fields into a Playwright [FormData](https://playwright.dev/python/docs/api/class-formdata) instance, and finally assigns it to the `form=` argument of [APIRequestContext.fetch()](https://playwright.dev/python/docs/api/class-apirequestcontext#api-request-context-fetch). Playwright sets the `Content-Type` header to `application/x-www-form-urlencoded` automatically.

For lists of scalars, Stoma calls the `append()` method of `FormData` to add the form data.

## UploadFile

`UploadFile` declares a file upload field.

```python
from stoma import APIRoute, APIRouter, ResponseSpec, UploadFile

router = APIRouter()

@router.post("/upload")
class UploadAvatar(APIRoute):
    """Upload a user avatar."""

    avatar: UploadFile
```

`UploadFile` currently takes a single argument, `path`, of type `pathlib.Path`, which gives the path of the local file. Stoma fills the value of `path` into a Playwright [FormData](https://playwright.dev/python/docs/api/class-formdata) instance, and finally assigns it to the `multipart=` argument of [APIRequestContext.fetch()](https://playwright.dev/python/docs/api/class-apirequestcontext#api-request-context-fetch). Playwright infers the filename and sets the `Content-Type` header to `multipart/form-data`.

## Form() + UploadFile

`Form()` fields and `UploadFile` fields can be used together. Stoma assigns the filled [FormData](https://playwright.dev/python/docs/api/class-formdata) instance to the `multipart=` argument of [APIRequestContext.fetch()](https://playwright.dev/python/docs/api/class-apirequestcontext#api-request-context-fetch), and Playwright sets the `Content-Type` header to `multipart/form-data`.

```python
import pathlib
from typing import Annotated
from stoma import APIRoute, APIRouter, Form, ResponseSpec, UploadFile

router = APIRouter()

@router.post("/upload-mix")
class UploadWithForm(APIRoute):
    """Send a form field and a file together."""

    username: Annotated[str, Form()]
    avatar: UploadFile
```

⚠️ Note: when there are `Form()` or `UploadFile` parameters, there must be no `Body()` parameter.

### Binary body, Postman style

From the examples above you can see that as long as there is an `UploadFile` field, Stoma sets the header to `multipart/form-data`. But OpenAPI also allows uploading a single file with the `Content-Type` header set to the file's [media type](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/MIME_types) — the same as the binary Body in Postman (single file upload).

Stoma supports this with `upload_as_multipart=False`: the request body is replaced with the raw bytes of the file (rather than multipart encoding), and the `Content-Type` header is set to the file's media type.

```python
import pathlib
from stoma import APIRoute, APIRouter, ResponseSpec, UploadFile

router = APIRouter()

@router.post("/raw-upload", upload_as_multipart=False)
class RawUpload(APIRoute):
    """Upload raw bytes."""

    file: UploadFile
```

`upload_as_multipart=False` only takes effect in this case:

* the body contains exactly one `UploadFile` field and no other `Form()` fields.

## Omitting the mark

The `Path()`, `Query()`, `Header()` and `Body()` marks can be omitted.

Take a path parameter as the example: when `Path()` is omitted and the field name matches the path placeholder, it is recognized as a path parameter automatically.

```python
@router.get("/users/{user_id}")
class GetUserById(APIRoute):
    """Get a user by ID."""

    user_id: int
```

If the field has an alias, the alias has to match the path placeholder.

```python
@router.get("/users/{userId}")
class GetUserById(APIRoute):
    """Get a user by ID."""

    user_id: Annotated[int, Field(serialization_alias="userId")]
```

### Recognition order

Note that for any type of parameter, when there is an alias only the alias is compared; the field name is used only when there is no alias. Below, "parameter name" refers to the result of that competition between alias and field name.

When several kinds of parameter omit their mark, the recognition order is:

1. If the parameter name matches a path placeholder, it is recognized as a path parameter.
2. Check whether the type is a composite type; if it is, it is recognized as a request body parameter.
3. A non-composite type (a scalar) is recognized as a query parameter.
