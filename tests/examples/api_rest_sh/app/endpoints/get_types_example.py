"""
Generated from OpenAPI: get-types-example
Example structured data types
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, TypesModel
from ..router import router


@router.get("/types")
class GetTypesExample(APIRoute):
    """
    Example structured data types
    """

    on_200: ClassVar[JSONResponseSpec[TypesModel]] = JSONResponseSpec(
        status_code=200, media_type="application/json", model=TypesModel
    )
    on_default: ClassVar[JSONResponseSpec[ErrorModel]] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
