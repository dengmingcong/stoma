"""Updates a pet in the store with form data.。

Generated from OpenAPI: updatePetWithForm
Updates a pet resource based on the form data.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from stoma import APIRoute, ResponseSpec

from ..models import Pet
from ..router import router


@router.post("/pet/{petId}")
class UpdatePetWithForm(APIRoute):
    """Updates a pet in the store with form data.。

    Updates a pet resource based on the form data.
    """

    pet_id: Annotated[int, Field(serialization_alias="petId")]
    """ID of pet that needs to be updated"""
    name: str | None = None
    """Name of pet that needs to be updated"""
    status: str | None = None
    """Status of pet that needs to be updated"""

    @property
    def on_200_application_json(self) -> ResponseSpec[Pet]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=Pet)

    @property
    def on_200_application_xml(self) -> ResponseSpec[str]:
        return ResponseSpec(status_code=200, media_type="application/xml", expected_type=str)
