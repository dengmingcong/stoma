"""Return XML。

Generated from OpenAPI: get-xml
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/xml")
class GetXml(APIRoute):
    """Return XML。"""

    @property
    def on_200(self) -> ResponseSpec[str]:
        return ResponseSpec(
            status_code=200,
            media_type="application/json",
            expected_type=str,
        )

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200],
            media_type="application/problem+json",
            expected_type=ErrorModel,
        )
