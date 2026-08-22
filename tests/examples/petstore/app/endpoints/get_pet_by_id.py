"""Find pet by ID.。

Generated from OpenAPI: getPetById
Returns a single pet.
"""

from __future__ import annotations

from typing import Annotated, ClassVar

from pydantic import Field

from stoma import APIRoute, JSONResponseSpec, RawResponseSpec

from ..models import Pet
from ..router import router


@router.get("/pet/{petId}")
class GetPetById(APIRoute):
    """Find pet by ID.。

    Returns a single pet.
    """

    on_200_application_json: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        status_code=200, media_type="application/json", model=Pet
    )
    on_200_application_xml: ClassVar[RawResponseSpec[str]] = RawResponseSpec.text(
        status_code=200, media_type="application/xml"
    )
    pet_id: Annotated[int, Field(serialization_alias="petId")]
    """ID of pet to return"""
