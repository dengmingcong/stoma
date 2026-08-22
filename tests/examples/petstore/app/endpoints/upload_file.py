"""Uploads an image.。

Generated from OpenAPI: uploadFile
Upload image of the pet.
"""

from __future__ import annotations

from typing import Annotated, ClassVar

from pydantic import Field

from stoma import APIRoute, Header, JSONResponseSpec, UploadFile

from ..models import ApiResponse
from ..router import router


@router.post("/pet/{petId}/uploadImage", upload_as_multipart=False)
class UploadFile(APIRoute):
    """Uploads an image.。

    Upload image of the pet.
    """

    on_200: ClassVar[JSONResponseSpec[ApiResponse]] = JSONResponseSpec(
        status_code=200, media_type="application/json", model=ApiResponse
    )
    pet_id: Annotated[int, Field(serialization_alias="petId")]
    """ID of pet to update"""
    additional_metadata: Annotated[str | None, Field(serialization_alias="additionalMetadata")] = None
    """Additional Metadata"""
    content_type: Annotated[str, Header(), Field(serialization_alias="Content-Type")] = "application/octet-stream"
    body: UploadFile
