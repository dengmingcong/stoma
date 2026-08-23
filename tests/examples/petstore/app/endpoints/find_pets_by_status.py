"""Finds Pets by status.。

Generated from OpenAPI: findPetsByStatus
Multiple status values can be provided with comma separated strings.
"""

from __future__ import annotations

from stoma import APIRoute, EmptyResponseSpec, ResponseSpec

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
    def on_200_application_json(self) -> ResponseSpec[FindPetsByStatusResponse]:
        return ResponseSpec(
            status_code=200,
            media_type="application/json",
            expected_type=FindPetsByStatusResponse,
        )

    @property
    def on_400(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=400,
        )

    @property
    def on_default(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=lambda c: c not in [200, 400],
        )
