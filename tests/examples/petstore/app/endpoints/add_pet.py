"""Add a new pet to the store.。

Generated from OpenAPI: addPet
Add a new pet to the store.
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import Pet
from ..router import router


@router.post("/pet")
class AddPet(APIRoute):
    """Add a new pet to the store.。

    Add a new pet to the store.
    """

    body: Pet

    @property
    def on_200_application_json(self) -> ResponseSpec[Pet]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=Pet)

    @property
    def on_200_application_xml(self) -> ResponseSpec[str]:
        return ResponseSpec(status_code=200, media_type="application/xml", expected_type=str)
