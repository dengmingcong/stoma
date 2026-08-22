"""Redirect to a supplied URL。

Generated from OpenAPI: get-redirect-to
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/redirect-to")
class GetRedirectTo(APIRoute):
    """Redirect to a supplied URL。"""

    url: str
    """Absolute or relative redirect target"""
    status_code: int | None = None
    """3xx redirect status code to send"""

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: (
                c
                not in [
                    300,
                    301,
                    302,
                    303,
                    304,
                    305,
                    306,
                    307,
                    308,
                    309,
                    310,
                    311,
                    312,
                    313,
                    314,
                    315,
                    316,
                    317,
                    318,
                    319,
                    320,
                    321,
                    322,
                    323,
                    324,
                    325,
                    326,
                    327,
                    328,
                    329,
                    330,
                    331,
                    332,
                    333,
                    334,
                    335,
                    336,
                    337,
                    338,
                    339,
                    340,
                    341,
                    342,
                    343,
                    344,
                    345,
                    346,
                    347,
                    348,
                    349,
                    350,
                    351,
                    352,
                    353,
                    354,
                    355,
                    356,
                    357,
                    358,
                    359,
                    360,
                    361,
                    362,
                    363,
                    364,
                    365,
                    366,
                    367,
                    368,
                    369,
                    370,
                    371,
                    372,
                    373,
                    374,
                    375,
                    376,
                    377,
                    378,
                    379,
                    380,
                    381,
                    382,
                    383,
                    384,
                    385,
                    386,
                    387,
                    388,
                    389,
                    390,
                    391,
                    392,
                    393,
                    394,
                    395,
                    396,
                    397,
                    398,
                    399,
                ]
            ),
            media_type="application/problem+json",
            model=ErrorModel,
        )
