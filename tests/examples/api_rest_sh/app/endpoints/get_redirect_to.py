"""Redirect to a supplied URL。

Generated from OpenAPI: get-redirect-to
"""

from __future__ import annotations

from stoma import APIRoute, EmptyResponseSpec, ResponseSpec

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
    def on_300(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=300,
        )

    @property
    def on_301(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=301,
        )

    @property
    def on_302(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=302,
        )

    @property
    def on_303(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=303,
        )

    @property
    def on_304(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=304,
        )

    @property
    def on_305(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=305,
        )

    @property
    def on_306(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=306,
        )

    @property
    def on_307(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=307,
        )

    @property
    def on_308(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=308,
        )

    @property
    def on_309(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=309,
        )

    @property
    def on_310(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=310,
        )

    @property
    def on_311(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=311,
        )

    @property
    def on_312(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=312,
        )

    @property
    def on_313(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=313,
        )

    @property
    def on_314(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=314,
        )

    @property
    def on_315(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=315,
        )

    @property
    def on_316(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=316,
        )

    @property
    def on_317(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=317,
        )

    @property
    def on_318(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=318,
        )

    @property
    def on_319(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=319,
        )

    @property
    def on_320(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=320,
        )

    @property
    def on_321(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=321,
        )

    @property
    def on_322(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=322,
        )

    @property
    def on_323(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=323,
        )

    @property
    def on_324(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=324,
        )

    @property
    def on_325(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=325,
        )

    @property
    def on_326(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=326,
        )

    @property
    def on_327(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=327,
        )

    @property
    def on_328(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=328,
        )

    @property
    def on_329(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=329,
        )

    @property
    def on_330(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=330,
        )

    @property
    def on_331(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=331,
        )

    @property
    def on_332(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=332,
        )

    @property
    def on_333(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=333,
        )

    @property
    def on_334(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=334,
        )

    @property
    def on_335(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=335,
        )

    @property
    def on_336(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=336,
        )

    @property
    def on_337(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=337,
        )

    @property
    def on_338(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=338,
        )

    @property
    def on_339(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=339,
        )

    @property
    def on_340(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=340,
        )

    @property
    def on_341(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=341,
        )

    @property
    def on_342(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=342,
        )

    @property
    def on_343(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=343,
        )

    @property
    def on_344(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=344,
        )

    @property
    def on_345(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=345,
        )

    @property
    def on_346(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=346,
        )

    @property
    def on_347(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=347,
        )

    @property
    def on_348(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=348,
        )

    @property
    def on_349(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=349,
        )

    @property
    def on_350(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=350,
        )

    @property
    def on_351(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=351,
        )

    @property
    def on_352(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=352,
        )

    @property
    def on_353(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=353,
        )

    @property
    def on_354(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=354,
        )

    @property
    def on_355(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=355,
        )

    @property
    def on_356(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=356,
        )

    @property
    def on_357(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=357,
        )

    @property
    def on_358(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=358,
        )

    @property
    def on_359(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=359,
        )

    @property
    def on_360(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=360,
        )

    @property
    def on_361(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=361,
        )

    @property
    def on_362(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=362,
        )

    @property
    def on_363(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=363,
        )

    @property
    def on_364(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=364,
        )

    @property
    def on_365(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=365,
        )

    @property
    def on_366(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=366,
        )

    @property
    def on_367(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=367,
        )

    @property
    def on_368(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=368,
        )

    @property
    def on_369(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=369,
        )

    @property
    def on_370(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=370,
        )

    @property
    def on_371(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=371,
        )

    @property
    def on_372(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=372,
        )

    @property
    def on_373(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=373,
        )

    @property
    def on_374(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=374,
        )

    @property
    def on_375(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=375,
        )

    @property
    def on_376(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=376,
        )

    @property
    def on_377(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=377,
        )

    @property
    def on_378(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=378,
        )

    @property
    def on_379(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=379,
        )

    @property
    def on_380(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=380,
        )

    @property
    def on_381(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=381,
        )

    @property
    def on_382(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=382,
        )

    @property
    def on_383(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=383,
        )

    @property
    def on_384(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=384,
        )

    @property
    def on_385(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=385,
        )

    @property
    def on_386(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=386,
        )

    @property
    def on_387(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=387,
        )

    @property
    def on_388(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=388,
        )

    @property
    def on_389(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=389,
        )

    @property
    def on_390(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=390,
        )

    @property
    def on_391(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=391,
        )

    @property
    def on_392(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=392,
        )

    @property
    def on_393(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=393,
        )

    @property
    def on_394(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=394,
        )

    @property
    def on_395(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=395,
        )

    @property
    def on_396(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=396,
        )

    @property
    def on_397(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=397,
        )

    @property
    def on_398(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=398,
        )

    @property
    def on_399(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=399,
        )

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
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
            expected_type=ErrorModel,
        )
