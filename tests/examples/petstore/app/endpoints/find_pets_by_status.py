"""Finds Pets by status.。

Generated from OpenAPI: findPetsByStatus
Multiple status values can be provided with comma separated strings.
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec, RawResponseSpec

from ..models import FindPetsByStatusResponse
from ..router import router


@router.get("/pet/findByStatus")
class FindPetsByStatus(APIRoute):
    """Finds Pets by status.。

    Multiple status values can be provided with comma separated strings.
    """

    on_200_application_json: ClassVar[JSONResponseSpec[FindPetsByStatusResponse]] = JSONResponseSpec(
        status_code=200, media_type="application/json", model=FindPetsByStatusResponse
    )
    on_200_application_xml: ClassVar[RawResponseSpec[str]] = RawResponseSpec.text(
        status_code=200, media_type="application/xml"
    )
    status: str
    """Status values that need to be considered for filter"""
