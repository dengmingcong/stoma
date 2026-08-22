"""Echo multipart upload metadata。

Generated from OpenAPI: post-upload
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, UploadResponseBody
from ..router import router


@router.post("/uploads")
class PostUpload(APIRoute):
    """Echo multipart upload metadata。"""

    @property
    def on_200(self) -> JSONResponseSpec[UploadResponseBody]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=UploadResponseBody)

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
