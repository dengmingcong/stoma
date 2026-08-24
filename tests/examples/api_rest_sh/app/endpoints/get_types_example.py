"""
Generated from OpenAPI: get-types-example
Example structured data types
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel, TypesModel
from ..router import router


@router.get("/types")
class GetTypesExample(APIRoute):
    """
    Example structured data types
    """

    @property
    def on_200(self) -> ResponseSpec[TypesModel]:
        return ResponseSpec(
            status_code=200,
            media_type="application/json",
            expected_type=TypesModel,
        )

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200],
            media_type="application/problem+json",
            expected_type=ErrorModel,
        )
