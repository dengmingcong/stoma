"""Finds Pets by status.。

Generated from OpenAPI: findPetsByStatus
Multiple status values can be provided with comma separated strings.
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec, RawResponseSpec

from ..models import FindPetsByStatusResponse
from ..router import router


@router.get("/pet/findByStatus")
class FindPetsByStatus(APIRoute):
    """Finds Pets by status.。

    Multiple status values can be provided with comma separated strings.
    """

    status: str
    """Status values that need to be considered for filter"""

    @property
    def on_200_application_json(self) -> JSONResponseSpec[FindPetsByStatusResponse]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=FindPetsByStatusResponse)

    @property
    def on_200_application_xml(self) -> RawResponseSpec[str]:
        return RawResponseSpec(status_code=200, media_type="application/xml", target_type=str)
