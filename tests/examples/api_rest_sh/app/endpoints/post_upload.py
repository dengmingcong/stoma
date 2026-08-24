"""Echo multipart upload metadata。

Generated from OpenAPI: post-upload
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel, UploadResponseBody
from ..router import router


@router.post("/uploads")
class PostUpload(APIRoute):
    """Echo multipart upload metadata。"""

    @property
    def on_200(self) -> ResponseSpec[UploadResponseBody]:
        return ResponseSpec(
            status_code=200,
            media_type="application/json",
            expected_type=UploadResponseBody,
        )

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200],
            media_type="application/problem+json",
            expected_type=ErrorModel,
        )
