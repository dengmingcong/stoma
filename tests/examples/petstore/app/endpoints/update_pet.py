"""Update an existing pet.。

Generated from OpenAPI: updatePet
Update an existing pet by Id.
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import Pet
from ..router import router


@router.put("/pet")
class UpdatePet(APIRoute):
    """Update an existing pet.。

    Update an existing pet by Id.
    """

    body: Pet

    @property
    def on_200_application_json(self) -> ResponseSpec[Pet]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=Pet)

    @property
    def on_200_application_xml(self) -> ResponseSpec[str]:
        return ResponseSpec(status_code=200, media_type="application/xml", expected_type=str)
