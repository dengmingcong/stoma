"""Update an existing pet.。

Generated from OpenAPI: updatePet
Update an existing pet by Id.
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec, RawResponseSpec

from ..models import Pet
from ..router import router


@router.put("/pet")
class UpdatePet(APIRoute):
    """Update an existing pet.。

    Update an existing pet by Id.
    """

    body: Pet

    @property
    def on_200_application_json(self) -> JSONResponseSpec[Pet]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=Pet)

    @property
    def on_200_application_xml(self) -> RawResponseSpec[str]:
        return RawResponseSpec(status_code=200, media_type="application/xml", target_type=str)
