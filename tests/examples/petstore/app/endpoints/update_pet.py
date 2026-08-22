"""Update an existing pet.。

Generated from OpenAPI: updatePet
Update an existing pet by Id.
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec, RawResponseSpec

from ..models import Pet
from ..router import router


@router.put("/pet")
class UpdatePet(APIRoute):
    """Update an existing pet.。

    Update an existing pet by Id.
    """

    on_200_application_json: ClassVar[JSONResponseSpec[Pet]] = JSONResponseSpec(
        status_code=200, media_type="application/json", model=Pet
    )
    on_200_application_xml: ClassVar[RawResponseSpec[str]] = RawResponseSpec.text(
        status_code=200, media_type="application/xml"
    )
    body: Pet
