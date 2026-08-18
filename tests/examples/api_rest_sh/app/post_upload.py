"""Echo multipart upload metadata。

Generated from OpenAPI: post-upload
"""

from __future__ import annotations

from .models import UploadResponseBody, ErrorModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.post("/uploads")
class PostUpload(APIRoute[UploadResponseBody | ErrorModel]):
    """Echo multipart upload metadata。"""
