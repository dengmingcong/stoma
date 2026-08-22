"""Updates a pet in the store with form data.。

Generated from OpenAPI: updatePetWithForm
Updates a pet resource based on the form data.
"""

from __future__ import annotations

from typing import Annotated, ClassVar

from pydantic import Field

from stoma import APIRoute, JSONResponseSpec, RawResponseSpec

from ..models import Pet
from ..router import router


@router.post("/pet/{petId}")
class UpdatePetWithForm(APIRoute):
    """Updates a pet in the store with form data.。

    Updates a pet resource based on the form data.
    """

    on_200_application_json: ClassVar[JSONResponseSpec[Pet]] = JSONResponseSpec(
        status_code=200, media_type="application/json", model=Pet
    )
    on_200_application_xml: ClassVar[RawResponseSpec[str]] = RawResponseSpec.text(
        status_code=200, media_type="application/xml"
    )
    pet_id: Annotated[int, Field(serialization_alias="petId")]
    """ID of pet that needs to be updated"""
    name: str | None = None
    """Name of pet that needs to be updated"""
    status: str | None = None
    """Status of pet that needs to be updated"""
