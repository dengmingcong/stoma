"""Uploads an image.。

Generated from OpenAPI: uploadFile
Upload image of the pet.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from stoma import APIRoute, EmptyResponseSpec, Header, ResponseSpec, UploadFile

from ..models import ApiResponse
from ..router import router


@router.post("/pet/{petId}/uploadImage", upload_as_multipart=False)
class UploadFile(APIRoute):
    """Uploads an image.。

    Upload image of the pet.
    """

    pet_id: Annotated[int, Field(serialization_alias="petId")]
    """ID of pet to update"""
    additional_metadata: Annotated[str | None, Field(serialization_alias="additionalMetadata")] = None
    """Additional Metadata"""
    content_type: Annotated[str, Header(), Field(serialization_alias="Content-Type")] = "application/octet-stream"
    body: UploadFile

    @property
    def on_200(self) -> ResponseSpec[ApiResponse]:
        return ResponseSpec(
            status_code=200,
            media_type="application/json",
            expected_type=ApiResponse,
        )

    @property
    def on_400(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=400,
        )

    @property
    def on_404(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=404,
        )

    @property
    def on_default(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=lambda c: c not in [200, 400, 404],
        )
