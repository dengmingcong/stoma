"""集成测试用的 FastAPI Mock Server。

替换旧的 HTTPHandler（基于 BaseHTTPRequestHandler），提供与 stoma 测试需求匹配的端点。
通过 Pydantic 模型与 stoma 测试共享类型，复用 stoma 的 Pydantic 生态。
"""

from typing import Annotated, Any

from fastapi import FastAPI, File, Form, Query, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.datastructures import UploadFile as StarletteUploadFile


# 共享模型（与 stoma 测试期望对齐）
class UserData(BaseModel):
    """用户数据模型。"""

    id: int
    name: str
    email: str | None = None


class CreateUserRequest(BaseModel):
    """创建用户的请求体。"""

    name: str
    email: str


app = FastAPI(title="Stoma Mock Server", docs_url=None, redoc_url=None)


# ===== 正常响应（与原 HTTPHandler 行为一致）=====


@app.get("/users", response_model=list[UserData])
def list_users(limit: int = 20, offset: int = 0) -> list[UserData]:
    """GET /users：返回 limit 个用户，从 offset 开始。"""
    return [UserData(id=i, name=f"User {i}", email=f"user{i}@example.com") for i in range(offset, offset + limit)]


@app.get("/users/{user_id}", response_model=UserData)
def get_user(user_id: int) -> UserData:
    """GET /users/{user_id}：返回单个用户。"""
    return UserData(
        id=user_id,
        name=f"User {user_id}",
        email=f"user{user_id}@example.com",
    )


@app.get("/items", response_model=list[dict[str, Any]])
def list_items(
    category: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> list[dict[str, Any]]:
    """GET /items：返回 limit 个 items，category 可选。"""
    cat = category or "default"
    return [{"id": i, "name": f"Item {i}", "category": cat} for i in range(limit)]


@app.post("/users", response_model=UserData, status_code=201)
def create_user(body: CreateUserRequest) -> UserData:
    """POST /users：单 body Pydantic 模型（stoma 序列化 = flat）。

    参数名 `body` 不与 stoma 字段名 `data` 冲突，
    FastAPI 期望 `{"name": ..., "email": ...}`（flat）。
    """
    return UserData(id=999, name=body.name, email=body.email)


@app.post("/echo")
def echo(body: dict[str, Any]) -> dict[str, Any]:
    """POST /echo：原样返回请求体（用于调试）。"""
    return body


# ===== 内容类型派发（覆盖原 HTTPHandler 各种 content-type）=====


@app.get("/health")
def health_check(status: str = "ok") -> dict[str, str]:
    """GET /health：返回 status 字段。"""
    return {"status": status}


@app.get("/text")
def get_text() -> Response:
    """GET /text：text/plain utf-8 "hello world"。

    必须显式 Response，否则 FastAPI 会把 -> str 编码为 JSON。
    """
    return Response(content=b"hello world", media_type="text/plain; charset=utf-8")


@app.get("/bytes")
def get_bytes() -> Response:
    """GET /bytes：application/octet-stream 4 字节。"""
    return Response(content=b"\x00\x01\x02\x03", media_type="application/octet-stream")


@app.get("/notype")
def get_notype() -> Response:
    """GET /notype：无 Content-Type 响应（特殊用例）。"""
    return Response(content=b"plain text body", media_type=None)


@app.get("/empty")
def get_empty() -> Response:
    """GET /empty：204 No Content（无 content-type）。"""
    return Response(status_code=204)


@app.get("/problem-json")
def get_problem_json() -> Response:
    """GET /problem-json：application/problem+json。"""
    return Response(
        content=b'{"detail": "everything is fine", "status": 200}',
        media_type="application/problem+json",
    )


@app.get("/charset-json")
def get_charset_json() -> Response:
    """GET /charset-json：application/json; charset=utf-8。"""
    return Response(
        content=b'{"hello": "world"}',
        media_type="application/json; charset=utf-8",
    )


# ===== 错误响应（4xx/5xx + body）=====


@app.get("/nonexistent")
def nonexistent() -> JSONResponse:
    """GET /nonexistent：404 + JSON body。"""
    return JSONResponse(status_code=404, content={"error": "Not found"})


@app.get("/server-error-json")
def get_server_error_json() -> JSONResponse:
    """GET /server-error-json：500 + JSON body。"""
    return JSONResponse(status_code=500, content={"error": "internal error"})


@app.get("/server-error-text")
def get_server_error_text() -> Response:
    """GET /server-error-text：500 + text body。"""
    return Response(
        status_code=500,
        content=b"internal error",
        media_type="text/plain; charset=utf-8",
    )


# ===== Body Multiple Parameters =====


@app.post("/users-embed")
async def create_user_embed(request: Request) -> JSONResponse:
    """POST /users-embed：Body(embed=True) 测试。

    stoma 发送 `{"data": {...}}`（字段名 = data）。
    用 Request 直接读 body 绕过 FastAPI 自动解析（避免 `data` 字段名冲突）。
    返回 201 + UserData。
    """
    body = await request.json()
    inner = body.get("data", body)
    user = UserData(id=999, name=inner.get("name", ""), email=inner.get("email", ""))
    return JSONResponse(status_code=201, content=user.model_dump())


@app.post("/importance")
async def set_importance(request: Request) -> dict[str, int]:
    """POST /importance：标量 Body() 测试，importance 在顶层。

    stoma 发送 `{"importance": 5}`。用 Request 直接读 body 避免 FastAPI 标量被误判为 query。
    """
    body = await request.json()
    return {"received": body.get("importance", 0)}


@app.post("/multi")
async def create_multi(request: Request) -> dict[str, Any]:
    """POST /multi：多 body 参数测试，item + importance 在顶层。

    用 Request 直接读 body 避免 FastAPI 多参数解析。
    """
    body = await request.json()
    return {
        "name": body.get("item", {}).get("name", ""),
        "importance": body.get("importance", 0),
    }


@app.post("/echo-headers")
async def echo_headers(request: Request) -> dict[str, str]:
    """POST /echo-headers：回显 Content-Type header。

    用于验证 Body(media_type=...) 是否真正设置到 wire 上的 Content-Type。

    :param request: FastAPI Request 对象。
    :return: dict 包含 content-type header 值。
    """
    return {"content_type": request.headers.get("content-type", "")}


@app.post("/echo-headers-override")
async def echo_headers_override(request: Request) -> dict[str, str]:
    """POST /echo-headers-override：回显 Content-Type header。

    用于验证 Header(Content-Type) 覆盖 Body(media_type=) 的优先级。
    与 ``/echo-headers`` 行为一致；单独注册是为避免占用 ``/echo-headers`` 路径。

    :param request: FastAPI Request 对象。
    :return: dict 包含 content-type header 值。
    """
    return {"content_type": request.headers.get("content-type", "")}


@app.post("/echo-body")
async def echo_body(request: Request) -> JSONResponse:
    """POST /echo-body：回显原始 body 与 Content-Type。

    用于验证 ``Annotated[str, Body(media_type=...)]`` 字符串标量 body 的
    wire format。用 ``request.body()`` 读裸字节（绕过 FastAPI 自动 JSON
    解析），返回 ``{"body": <string>, "content_type": <header>}``。

    :param request: FastAPI Request 对象。
    :return: 原始 body 字符串与 Content-Type header 值。
    """
    raw = await request.body()
    return JSONResponse(content={
        "body": raw.decode("utf-8"),
        "content_type": request.headers.get("content-type", ""),
    })


@app.head("/probe")
def probe_head() -> Response:
    """HEAD /probe：探测端点，验证 HEAD 方法支持。

    HEAD 请求不返回 body（Starlette 自动丢弃）。
    使用无 content-type 的 Response，避免 Client 尝试解析 JSON。
    """
    return Response(status_code=200)


@app.options("/probe")
def probe_options() -> JSONResponse:
    """OPTIONS /probe：探测端点，验证 OPTIONS 方法支持。"""
    return JSONResponse(content={"method": "OPTIONS"}, status_code=200)


# ===== Multipart/Form-Data 端点 =====


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> dict[str, Any]:
    """POST /upload：接收 multipart/form-data 单文件。

    :param file: 上传的文件。
    :return: 文件名、大小、内容类型。
    """
    content = await file.read()
    return {
        "filename": file.filename,
        "size": len(content),
        "content_type": file.content_type,
    }


@app.post("/upload-multi")
async def upload_multi(files: list[UploadFile] = File(...)) -> dict[str, Any]:
    """POST /upload-multi：接收 multipart/form-data 多文件。

    :param files: 上传的文件列表。
    :return: 文件名列表和总大小。
    """
    total_size = 0
    filenames = []
    for f in files:
        content = await f.read()
        total_size += len(content)
        filenames.append(f.filename)
    return {
        "filenames": filenames,
        "total_size": total_size,
    }


@app.post("/upload-optional")
async def upload_optional(file: UploadFile | None = File(None)) -> dict[str, Any]:
    """POST /upload-optional：接收可选文件上传，不传时返回 None 占位。

    :param file: 可选上传文件；不传时为 ``None``。
    :return: 文件名、大小、内容类型；缺省时三个字段都为 ``None`` / 0。
    """
    if file is None:
        return {"filename": None, "size": 0, "content_type": None}
    content = await file.read()
    return {"filename": file.filename, "size": len(content), "content_type": file.content_type}


@app.post("/upload-files-optional")
async def upload_files_optional(files: list[UploadFile] | None = File(None)) -> dict[str, Any]:
    """POST /upload-files-optional：接收可选多文件上传，不传时返回空列表占位。

    :param files: 可选多文件列表；不传时为 ``None``（与空列表统一处理）。
    :return: 文件名列表和总大小（无文件时为 ``[]`` / 0）。
    """
    if not files:
        return {"filenames": [], "total_size": 0}
    filenames = []
    total_size = 0
    for f in files:
        content = await f.read()
        total_size += len(content)
        filenames.append(f.filename)
    return {"filenames": filenames, "total_size": total_size}


@app.post("/login")
async def login(request: Request) -> dict[str, Any]:
    """POST /login：接收 form data。

    stoma 序列化约定：标量字段原值写入，list 字段逐元素 ``append`` 成同名多 part。
    FastAPI 的 ``Form()`` 字段无法同时兼容单值与多值，因此用 ``Request`` 直接读 form：
    单值字段取原值，重复字段（同名多次出现）保留为 ``list[str]``。

    同时覆盖 ``LoginRoute``（多个标量 ``Form()``）和 ``LoginFlatRoute``（BaseModel + Form，
    子字段平展）—— 两者 wire 格式相同。

    :param request: FastAPI Request 对象。
    :return: 解析后的表单数据，重复 key 合并为 ``list``。
    """
    form = await request.form()
    result: dict[str, Any] = {}
    for key in form:
        values = form.getlist(key)
        result[key] = values[0] if len(values) == 1 else values
    return result


@app.post("/login-list")
async def login_list(tags: Annotated[list[str], Form()]) -> dict[str, Any]:
    """POST /login-list：接收标量列表 Form 字段。

    stoma 对 ``Annotated[list[str], Form()]`` 逐元素 ``append``，wire 上是重复 key 的
    urlencoded body。FastAPI 的 ``list[str] = Form()`` 直接把重复 key 收敛为 list。

    :param tags: 重复 key 解析出的字符串列表。
    :return: 原样回显 tags 列表。
    """
    return {"tags": tags}


@app.post("/upload-mix")
async def upload_mix(request: Request) -> dict[str, Any]:
    """POST /upload-mix：多个标量 Form 字段 + UploadFile 共存。

    stoma 发送 multipart/form-data：标量 form 字段原值写入、list 字段逐元素 ``append``，
    再加单文件 ``avatar``。用 ``Request`` 手动 parse 以同时兼容单值与重复 key。
    文件字段通过 ``isinstance(value, StarletteUploadFile)`` 识别
    （注意：``fastapi.UploadFile`` 与 ``starlette.datastructures.UploadFile``
    是不同类，form 解析器产出 Starlette 版）。

    :param request: FastAPI Request 对象。
    :return: 表单字段值（重复 key 合并为 ``list``）+ 文件元信息。
    """
    form = await request.form()
    fields: dict[str, Any] = {}
    file_meta: dict[str, Any] = {}
    for key, value in form.multi_items():
        if isinstance(value, StarletteUploadFile):
            content = await value.read()
            file_meta = {
                "filename": value.filename,
                "size": len(content),
                "content_type": value.content_type,
            }
        elif key in fields:
            existing = fields[key]
            fields[key] = [*existing, value] if isinstance(existing, list) else [existing, value]
        else:
            fields[key] = value
    return {**fields, **file_meta}


@app.post("/upload-raw")
async def upload_raw(request: Request) -> dict[str, Any]:
    """POST /upload-raw：raw body 上传，验证 wire-level 序列化。

    与 /upload 不同，/upload-raw 不解析 multipart——整个 body 是裸字节，
    Content-Type 头标识文件 mime（来自 client.mimetypes.guess_type）。

    :param request: FastAPI Request 对象。
    :return: 字节大小和 content-type。
    """
    body = await request.body()
    return {
        "size": len(body),
        "content_type": request.headers.get("content-type", ""),
    }


@app.post("/upload-raw-override")
async def upload_raw_override(request: Request) -> dict[str, Any]:
    """POST /upload-raw-override：raw body 上传，回显 Content-Type。

    与 ``/upload-raw`` 行为一致；单独注册是为避免占用 ``/upload-raw`` 路径。
    """
    body = await request.body()
    return {
        "size": len(body),
        "content_type": request.headers.get("content-type", ""),
    }
