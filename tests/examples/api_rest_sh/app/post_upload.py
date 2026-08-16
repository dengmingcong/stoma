"""Echo multipart upload metadata。

Generated from OpenAPI: post-upload
"""

from __future__ import annotations

from .models import UploadResponseBody
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.post("/uploads")
class PostUpload(APIRoute[UploadResponseBody]):
    """Echo multipart upload metadata。
    """
