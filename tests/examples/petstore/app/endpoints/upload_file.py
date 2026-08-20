"""Uploads an image.。

Generated from OpenAPI: uploadFile
Upload image of the pet.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from stoma import APIRoute, Header, UploadFile

from ..models import ApiResponse
from ..router import router


@router.post("/pet/{petId}/uploadImage", upload_as_multipart=False)
class UploadFile(APIRoute[ApiResponse]):
    """Uploads an image.。

    Upload image of the pet.
    """

    pet_id: Annotated[int, Field(serialization_alias="petId")]
    """ID of pet to update"""
    additional_metadata: Annotated[str | None, Field(serialization_alias="additionalMetadata")] = None
    """Additional Metadata"""
    content_type: Annotated[str, Header(), Field(serialization_alias="Content-Type")] = "application/octet-stream"
    body: UploadFile
