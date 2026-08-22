"""
Generated from OpenAPI: get-types-example
Example structured data types
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, TypesModel
from ..router import router


@router.get("/types")
class GetTypesExample(APIRoute):
    """
    Example structured data types
    """

    @property
    def on_200(self) -> JSONResponseSpec[TypesModel]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=TypesModel)

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
