"""Add a new pet to the store.。

Generated from OpenAPI: addPet
Add a new pet to the store.
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec, RawResponseSpec

from ..models import Pet
from ..router import router


@router.post("/pet")
class AddPet(APIRoute):
    """Add a new pet to the store.。

    Add a new pet to the store.
    """

    body: Pet

    @property
    def on_200_application_json(self) -> JSONResponseSpec[Pet]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=Pet)

    @property
    def on_200_application_xml(self) -> RawResponseSpec[str]:
        return RawResponseSpec(status_code=200, media_type="application/xml", target_type=str)
