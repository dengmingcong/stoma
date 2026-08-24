"""Find pet by ID.。

Generated from OpenAPI: getPetById
Returns a single pet.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from stoma import APIRoute, EmptyResponseSpec, ResponseSpec

from ..models import Pet
from ..router import router


@router.get("/pet/{petId}")
class GetPetById(APIRoute):
    """Find pet by ID.。

    Returns a single pet.
    """

    pet_id: Annotated[int, Field(serialization_alias="petId")]
    """ID of pet to return"""

    @property
    def on_200_application_json(self) -> ResponseSpec[Pet]:
        return ResponseSpec(
            status_code=200,
            media_type="application/json",
            expected_type=Pet,
        )

    @property
    def on_200_application_xml(self) -> ResponseSpec[Pet]:
        return ResponseSpec(
            status_code=200,
            media_type="application/xml",
            expected_type=Pet,
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
