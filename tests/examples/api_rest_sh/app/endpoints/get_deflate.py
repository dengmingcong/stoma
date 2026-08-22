"""Return an explicitly compressed response。

Generated from OpenAPI: get-deflate
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/deflate")
class GetDeflate(APIRoute):
    """Return an explicitly compressed response。"""

    on_default: ClassVar[JSONResponseSpec[ErrorModel]] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
