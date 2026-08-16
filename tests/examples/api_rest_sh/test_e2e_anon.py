"""examples/api_rest_sh/test_e2e_anon.py。

13 个匿名（无鉴权）端到端场景，发送到真实 api.rest.sh。

场景对应表：
1. test_get_method → GetMethod(status=200) → status==200
2. test_get_anything_path → GetAnythingPath(path="foo/bar") → status==200, "foo/bar" in text
3. test_post_method → PostMethod(data={"key": "value"}) → status==200
4. test_post_login → PostLogin(username="alice") → status==200, "alice" in text
5. test_post_upload → PostUpload(file=UploadFile(path=tmp_path/"hello.txt")) → status==200, "hello.txt" in text
6. test_patch_book → PatchBook(book_id="123", body=[{...}]) → status==200
7. test_delete_book → DeleteBook(book_id="123") → status==204
8. test_head_method → HeadMethod() → status==200
9. test_options_method → OptionsMethod() → status==200
10. test_get_bytes → GetBytes(n=100) → status==200, octet-stream, len>=50
11. test_get_accept_image → GetAcceptImage() → status==200, image in content-type
12. test_get_status_404 → GetStatus(code=404) → status==404, problem+json in content-type
13. test_get_etag → GetEtag(etag='"abc"', if_none_match='"abc"') → status==304
"""

from __future__ import annotations

import pytest

from src import UploadFile
from src.client import Client
from tests.examples.api_rest_sh.app.delete_book import DeleteBook
from tests.examples.api_rest_sh.app.get_accept_image import GetAcceptImage
from tests.examples.api_rest_sh.app.get_anything_path import GetAnythingPath
from tests.examples.api_rest_sh.app.get_bytes import GetBytes
from tests.examples.api_rest_sh.app.get_etag import GetEtag
from tests.examples.api_rest_sh.app.get_method import GetMethod
from tests.examples.api_rest_sh.app.get_status import GetStatus
from tests.examples.api_rest_sh.app.head_method import HeadMethod
from tests.examples.api_rest_sh.app.options_method import OptionsMethod
from tests.examples.api_rest_sh.app.patch_book import PatchBook
from tests.examples.api_rest_sh.app.post_login import PostLogin
from tests.examples.api_rest_sh.app.post_method import PostMethod
from tests.examples.api_rest_sh.app.post_upload import PostUpload


def test_get_method(e2e_client: Client) -> None:
    """GET /get：返回默认 status=200。"""
    response = e2e_client.send(GetMethod(status=200))
    assert response.raw.status == 200


def test_get_anything_path(e2e_client: Client) -> None:
    """GET /anything/{path}：回显路径参数。"""
    response = e2e_client.send(GetAnythingPath(path="foo/bar"))
    assert response.raw.status == 200
    text = response.raw.text()
    assert "foo/bar" in text


def test_post_method(e2e_client: Client) -> None:
    """POST /post：回显请求体。"""
    response = e2e_client.send(PostMethod(data={"key": "value"}))
    assert response.raw.status == 200


def test_post_login(e2e_client: Client) -> None:
    """POST /login：表单提交 username，返回 token 响应。"""
    response = e2e_client.send(PostLogin(username="alice"))
    assert response.raw.status == 200
    text = response.raw.text()
    assert "alice" in text


def test_post_upload(e2e_client: Client, tmp_path: pytest.Path) -> None:
    """POST /uploads：上传 multipart 文件。"""
    file_path = tmp_path / "hello.txt"
    file_path.write_text("hello world")
    response = e2e_client.send(PostUpload(file=UploadFile(path=file_path)))
    assert response.raw.status == 200
    text = response.raw.text()
    assert "hello.txt" in text


def test_patch_book(e2e_client: Client) -> None:
    """PATCH /books/{book-id}：JSON Patch 更新，body 为 patch 操作列表。"""
    response = e2e_client.send(
        PatchBook(
            book_id="123",
            body=[{"op": "replace", "path": "/title", "value": "new"}],
        ),
    )
    assert response.raw.status == 200


def test_delete_book(e2e_client: Client) -> None:
    """DELETE /books/{book-id}：删除资源，返回 204。"""
    response = e2e_client.send(DeleteBook(book_id="123"))
    assert response.raw.status == 204


def test_head_method(e2e_client: Client) -> None:
    """HEAD /head：返回 200（无响应体）。"""
    response = e2e_client.send(HeadMethod())
    assert response.raw.status == 200


def test_options_method(e2e_client: Client) -> None:
    """OPTIONS /options：返回允许的方法。"""
    response = e2e_client.send(OptionsMethod())
    assert response.raw.status == 200


def test_get_bytes(e2e_client: Client) -> None:
    """GET /bytes/{n}：返回 n 个随机字节。"""
    response = e2e_client.send(GetBytes(n=100))
    assert response.raw.status == 200
    content_type = response.raw.headers.get("content-type", "")
    assert "octet-stream" in content_type
    body = response.raw.body()
    assert len(body) >= 50


def test_get_accept_image(e2e_client: Client) -> None:
    """GET /image：根据 Accept header 返回图片。"""
    response = e2e_client.send(GetAcceptImage())
    assert response.raw.status == 200
    content_type = response.raw.headers.get("content-type", "")
    assert "image" in content_type


def test_get_status_404(e2e_client: Client) -> None:
    """GET /status/{code}：返回指定 status code，404 时 content-type 为 problem+json。"""
    response = e2e_client.send(GetStatus(code=404))
    assert response.raw.status == 404
    content_type = response.raw.headers.get("content-type", "")
    assert "problem+json" in content_type


def test_get_etag(e2e_client: Client) -> None:
    """GET /etag/{etag}：带 If-None-Match header，匹配时返回 304。"""
    response = e2e_client.send(
        GetEtag(etag='"abc"', if_none_match='"abc"'),
    )
    assert response.raw.status == 304
