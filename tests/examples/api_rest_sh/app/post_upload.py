"""Echo multipart upload metadata。

Generated from OpenAPI: post-upload
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import ErrorModel, UploadResponseBody

router = APIRouter()


@router.post("/uploads")
class PostUpload(APIRoute[UploadResponseBody | ErrorModel]):
    """Echo multipart upload metadata。"""
