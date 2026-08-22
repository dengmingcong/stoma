"""Echo multipart upload metadata。

Generated from OpenAPI: post-upload
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, UploadResponseBody
from ..router import router


@router.post("/uploads")
class PostUpload(APIRoute):
    """Echo multipart upload metadata。"""

    on_200: ClassVar[JSONResponseSpec[UploadResponseBody]] = JSONResponseSpec(
        status_code=200, media_type="application/json", model=UploadResponseBody
    )
    on_default: ClassVar[JSONResponseSpec[ErrorModel]] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
