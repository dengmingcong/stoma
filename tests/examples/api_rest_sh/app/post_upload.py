"""Echo multipart upload metadata。

Generated from OpenAPI: post-upload
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute
from .models import UploadResponseBody, ErrorModel

router = APIRouter()


@router.post("/uploads")
class PostUpload(APIRoute[UploadResponseBody | ErrorModel]):
    """Echo multipart upload metadata。"""
