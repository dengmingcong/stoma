"""
Generated from OpenAPI: get-status
Status code example
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from stoma import APIRoute, EmptyResponseSpec, ResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/status/{code}")
class GetStatus(APIRoute):
    """
    Status code example
    """

    code: int
    """Status code to return"""
    retry_after: Annotated[str | None, Field(serialization_alias="retry-after")] = None
    """Retry-After header value"""
    x_retry_in: Annotated[str | None, Field(serialization_alias="x-retry-in")] = None
    """X-Retry-In header value"""

    @property
    def on_100(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=100,
        )

    @property
    def on_101(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=101,
        )

    @property
    def on_102(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=102,
        )

    @property
    def on_103(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=103,
        )

    @property
    def on_104(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=104,
        )

    @property
    def on_105(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=105,
        )

    @property
    def on_106(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=106,
        )

    @property
    def on_107(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=107,
        )

    @property
    def on_108(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=108,
        )

    @property
    def on_109(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=109,
        )

    @property
    def on_110(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=110,
        )

    @property
    def on_111(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=111,
        )

    @property
    def on_112(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=112,
        )

    @property
    def on_113(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=113,
        )

    @property
    def on_114(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=114,
        )

    @property
    def on_115(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=115,
        )

    @property
    def on_116(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=116,
        )

    @property
    def on_117(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=117,
        )

    @property
    def on_118(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=118,
        )

    @property
    def on_119(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=119,
        )

    @property
    def on_120(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=120,
        )

    @property
    def on_121(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=121,
        )

    @property
    def on_122(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=122,
        )

    @property
    def on_123(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=123,
        )

    @property
    def on_124(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=124,
        )

    @property
    def on_125(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=125,
        )

    @property
    def on_126(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=126,
        )

    @property
    def on_127(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=127,
        )

    @property
    def on_128(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=128,
        )

    @property
    def on_129(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=129,
        )

    @property
    def on_130(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=130,
        )

    @property
    def on_131(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=131,
        )

    @property
    def on_132(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=132,
        )

    @property
    def on_133(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=133,
        )

    @property
    def on_134(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=134,
        )

    @property
    def on_135(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=135,
        )

    @property
    def on_136(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=136,
        )

    @property
    def on_137(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=137,
        )

    @property
    def on_138(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=138,
        )

    @property
    def on_139(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=139,
        )

    @property
    def on_140(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=140,
        )

    @property
    def on_141(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=141,
        )

    @property
    def on_142(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=142,
        )

    @property
    def on_143(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=143,
        )

    @property
    def on_144(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=144,
        )

    @property
    def on_145(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=145,
        )

    @property
    def on_146(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=146,
        )

    @property
    def on_147(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=147,
        )

    @property
    def on_148(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=148,
        )

    @property
    def on_149(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=149,
        )

    @property
    def on_150(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=150,
        )

    @property
    def on_151(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=151,
        )

    @property
    def on_152(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=152,
        )

    @property
    def on_153(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=153,
        )

    @property
    def on_154(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=154,
        )

    @property
    def on_155(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=155,
        )

    @property
    def on_156(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=156,
        )

    @property
    def on_157(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=157,
        )

    @property
    def on_158(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=158,
        )

    @property
    def on_159(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=159,
        )

    @property
    def on_160(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=160,
        )

    @property
    def on_161(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=161,
        )

    @property
    def on_162(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=162,
        )

    @property
    def on_163(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=163,
        )

    @property
    def on_164(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=164,
        )

    @property
    def on_165(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=165,
        )

    @property
    def on_166(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=166,
        )

    @property
    def on_167(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=167,
        )

    @property
    def on_168(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=168,
        )

    @property
    def on_169(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=169,
        )

    @property
    def on_170(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=170,
        )

    @property
    def on_171(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=171,
        )

    @property
    def on_172(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=172,
        )

    @property
    def on_173(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=173,
        )

    @property
    def on_174(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=174,
        )

    @property
    def on_175(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=175,
        )

    @property
    def on_176(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=176,
        )

    @property
    def on_177(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=177,
        )

    @property
    def on_178(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=178,
        )

    @property
    def on_179(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=179,
        )

    @property
    def on_180(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=180,
        )

    @property
    def on_181(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=181,
        )

    @property
    def on_182(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=182,
        )

    @property
    def on_183(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=183,
        )

    @property
    def on_184(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=184,
        )

    @property
    def on_185(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=185,
        )

    @property
    def on_186(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=186,
        )

    @property
    def on_187(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=187,
        )

    @property
    def on_188(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=188,
        )

    @property
    def on_189(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=189,
        )

    @property
    def on_190(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=190,
        )

    @property
    def on_191(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=191,
        )

    @property
    def on_192(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=192,
        )

    @property
    def on_193(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=193,
        )

    @property
    def on_194(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=194,
        )

    @property
    def on_195(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=195,
        )

    @property
    def on_196(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=196,
        )

    @property
    def on_197(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=197,
        )

    @property
    def on_198(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=198,
        )

    @property
    def on_199(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=199,
        )

    @property
    def on_200(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=200,
        )

    @property
    def on_201(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=201,
        )

    @property
    def on_202(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=202,
        )

    @property
    def on_203(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=203,
        )

    @property
    def on_204(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=204,
        )

    @property
    def on_205(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=205,
        )

    @property
    def on_206(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=206,
        )

    @property
    def on_207(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=207,
        )

    @property
    def on_208(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=208,
        )

    @property
    def on_209(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=209,
        )

    @property
    def on_210(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=210,
        )

    @property
    def on_211(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=211,
        )

    @property
    def on_212(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=212,
        )

    @property
    def on_213(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=213,
        )

    @property
    def on_214(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=214,
        )

    @property
    def on_215(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=215,
        )

    @property
    def on_216(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=216,
        )

    @property
    def on_217(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=217,
        )

    @property
    def on_218(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=218,
        )

    @property
    def on_219(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=219,
        )

    @property
    def on_220(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=220,
        )

    @property
    def on_221(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=221,
        )

    @property
    def on_222(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=222,
        )

    @property
    def on_223(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=223,
        )

    @property
    def on_224(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=224,
        )

    @property
    def on_225(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=225,
        )

    @property
    def on_226(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=226,
        )

    @property
    def on_227(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=227,
        )

    @property
    def on_228(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=228,
        )

    @property
    def on_229(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=229,
        )

    @property
    def on_230(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=230,
        )

    @property
    def on_231(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=231,
        )

    @property
    def on_232(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=232,
        )

    @property
    def on_233(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=233,
        )

    @property
    def on_234(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=234,
        )

    @property
    def on_235(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=235,
        )

    @property
    def on_236(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=236,
        )

    @property
    def on_237(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=237,
        )

    @property
    def on_238(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=238,
        )

    @property
    def on_239(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=239,
        )

    @property
    def on_240(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=240,
        )

    @property
    def on_241(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=241,
        )

    @property
    def on_242(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=242,
        )

    @property
    def on_243(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=243,
        )

    @property
    def on_244(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=244,
        )

    @property
    def on_245(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=245,
        )

    @property
    def on_246(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=246,
        )

    @property
    def on_247(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=247,
        )

    @property
    def on_248(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=248,
        )

    @property
    def on_249(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=249,
        )

    @property
    def on_250(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=250,
        )

    @property
    def on_251(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=251,
        )

    @property
    def on_252(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=252,
        )

    @property
    def on_253(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=253,
        )

    @property
    def on_254(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=254,
        )

    @property
    def on_255(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=255,
        )

    @property
    def on_256(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=256,
        )

    @property
    def on_257(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=257,
        )

    @property
    def on_258(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=258,
        )

    @property
    def on_259(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=259,
        )

    @property
    def on_260(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=260,
        )

    @property
    def on_261(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=261,
        )

    @property
    def on_262(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=262,
        )

    @property
    def on_263(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=263,
        )

    @property
    def on_264(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=264,
        )

    @property
    def on_265(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=265,
        )

    @property
    def on_266(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=266,
        )

    @property
    def on_267(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=267,
        )

    @property
    def on_268(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=268,
        )

    @property
    def on_269(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=269,
        )

    @property
    def on_270(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=270,
        )

    @property
    def on_271(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=271,
        )

    @property
    def on_272(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=272,
        )

    @property
    def on_273(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=273,
        )

    @property
    def on_274(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=274,
        )

    @property
    def on_275(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=275,
        )

    @property
    def on_276(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=276,
        )

    @property
    def on_277(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=277,
        )

    @property
    def on_278(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=278,
        )

    @property
    def on_279(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=279,
        )

    @property
    def on_280(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=280,
        )

    @property
    def on_281(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=281,
        )

    @property
    def on_282(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=282,
        )

    @property
    def on_283(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=283,
        )

    @property
    def on_284(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=284,
        )

    @property
    def on_285(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=285,
        )

    @property
    def on_286(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=286,
        )

    @property
    def on_287(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=287,
        )

    @property
    def on_288(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=288,
        )

    @property
    def on_289(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=289,
        )

    @property
    def on_290(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=290,
        )

    @property
    def on_291(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=291,
        )

    @property
    def on_292(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=292,
        )

    @property
    def on_293(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=293,
        )

    @property
    def on_294(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=294,
        )

    @property
    def on_295(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=295,
        )

    @property
    def on_296(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=296,
        )

    @property
    def on_297(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=297,
        )

    @property
    def on_298(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=298,
        )

    @property
    def on_299(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=299,
        )

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
    def on_400(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=400,
        )

    @property
    def on_401(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=401,
        )

    @property
    def on_402(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=402,
        )

    @property
    def on_403(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=403,
        )

    @property
    def on_404(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=404,
        )

    @property
    def on_405(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=405,
        )

    @property
    def on_406(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=406,
        )

    @property
    def on_407(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=407,
        )

    @property
    def on_408(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=408,
        )

    @property
    def on_409(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=409,
        )

    @property
    def on_410(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=410,
        )

    @property
    def on_411(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=411,
        )

    @property
    def on_412(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=412,
        )

    @property
    def on_413(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=413,
        )

    @property
    def on_414(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=414,
        )

    @property
    def on_415(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=415,
        )

    @property
    def on_416(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=416,
        )

    @property
    def on_417(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=417,
        )

    @property
    def on_418(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=418,
        )

    @property
    def on_419(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=419,
        )

    @property
    def on_420(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=420,
        )

    @property
    def on_421(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=421,
        )

    @property
    def on_422(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=422,
        )

    @property
    def on_423(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=423,
        )

    @property
    def on_424(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=424,
        )

    @property
    def on_425(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=425,
        )

    @property
    def on_426(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=426,
        )

    @property
    def on_427(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=427,
        )

    @property
    def on_428(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=428,
        )

    @property
    def on_429(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=429,
        )

    @property
    def on_430(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=430,
        )

    @property
    def on_431(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=431,
        )

    @property
    def on_432(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=432,
        )

    @property
    def on_433(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=433,
        )

    @property
    def on_434(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=434,
        )

    @property
    def on_435(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=435,
        )

    @property
    def on_436(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=436,
        )

    @property
    def on_437(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=437,
        )

    @property
    def on_438(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=438,
        )

    @property
    def on_439(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=439,
        )

    @property
    def on_440(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=440,
        )

    @property
    def on_441(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=441,
        )

    @property
    def on_442(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=442,
        )

    @property
    def on_443(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=443,
        )

    @property
    def on_444(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=444,
        )

    @property
    def on_445(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=445,
        )

    @property
    def on_446(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=446,
        )

    @property
    def on_447(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=447,
        )

    @property
    def on_448(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=448,
        )

    @property
    def on_449(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=449,
        )

    @property
    def on_450(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=450,
        )

    @property
    def on_451(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=451,
        )

    @property
    def on_452(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=452,
        )

    @property
    def on_453(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=453,
        )

    @property
    def on_454(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=454,
        )

    @property
    def on_455(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=455,
        )

    @property
    def on_456(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=456,
        )

    @property
    def on_457(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=457,
        )

    @property
    def on_458(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=458,
        )

    @property
    def on_459(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=459,
        )

    @property
    def on_460(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=460,
        )

    @property
    def on_461(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=461,
        )

    @property
    def on_462(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=462,
        )

    @property
    def on_463(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=463,
        )

    @property
    def on_464(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=464,
        )

    @property
    def on_465(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=465,
        )

    @property
    def on_466(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=466,
        )

    @property
    def on_467(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=467,
        )

    @property
    def on_468(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=468,
        )

    @property
    def on_469(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=469,
        )

    @property
    def on_470(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=470,
        )

    @property
    def on_471(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=471,
        )

    @property
    def on_472(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=472,
        )

    @property
    def on_473(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=473,
        )

    @property
    def on_474(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=474,
        )

    @property
    def on_475(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=475,
        )

    @property
    def on_476(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=476,
        )

    @property
    def on_477(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=477,
        )

    @property
    def on_478(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=478,
        )

    @property
    def on_479(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=479,
        )

    @property
    def on_480(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=480,
        )

    @property
    def on_481(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=481,
        )

    @property
    def on_482(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=482,
        )

    @property
    def on_483(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=483,
        )

    @property
    def on_484(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=484,
        )

    @property
    def on_485(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=485,
        )

    @property
    def on_486(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=486,
        )

    @property
    def on_487(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=487,
        )

    @property
    def on_488(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=488,
        )

    @property
    def on_489(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=489,
        )

    @property
    def on_490(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=490,
        )

    @property
    def on_491(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=491,
        )

    @property
    def on_492(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=492,
        )

    @property
    def on_493(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=493,
        )

    @property
    def on_494(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=494,
        )

    @property
    def on_495(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=495,
        )

    @property
    def on_496(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=496,
        )

    @property
    def on_497(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=497,
        )

    @property
    def on_498(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=498,
        )

    @property
    def on_499(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=499,
        )

    @property
    def on_500(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=500,
        )

    @property
    def on_501(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=501,
        )

    @property
    def on_502(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=502,
        )

    @property
    def on_503(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=503,
        )

    @property
    def on_504(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=504,
        )

    @property
    def on_505(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=505,
        )

    @property
    def on_506(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=506,
        )

    @property
    def on_507(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=507,
        )

    @property
    def on_508(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=508,
        )

    @property
    def on_509(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=509,
        )

    @property
    def on_510(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=510,
        )

    @property
    def on_511(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=511,
        )

    @property
    def on_512(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=512,
        )

    @property
    def on_513(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=513,
        )

    @property
    def on_514(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=514,
        )

    @property
    def on_515(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=515,
        )

    @property
    def on_516(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=516,
        )

    @property
    def on_517(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=517,
        )

    @property
    def on_518(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=518,
        )

    @property
    def on_519(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=519,
        )

    @property
    def on_520(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=520,
        )

    @property
    def on_521(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=521,
        )

    @property
    def on_522(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=522,
        )

    @property
    def on_523(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=523,
        )

    @property
    def on_524(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=524,
        )

    @property
    def on_525(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=525,
        )

    @property
    def on_526(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=526,
        )

    @property
    def on_527(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=527,
        )

    @property
    def on_528(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=528,
        )

    @property
    def on_529(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=529,
        )

    @property
    def on_530(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=530,
        )

    @property
    def on_531(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=531,
        )

    @property
    def on_532(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=532,
        )

    @property
    def on_533(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=533,
        )

    @property
    def on_534(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=534,
        )

    @property
    def on_535(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=535,
        )

    @property
    def on_536(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=536,
        )

    @property
    def on_537(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=537,
        )

    @property
    def on_538(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=538,
        )

    @property
    def on_539(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=539,
        )

    @property
    def on_540(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=540,
        )

    @property
    def on_541(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=541,
        )

    @property
    def on_542(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=542,
        )

    @property
    def on_543(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=543,
        )

    @property
    def on_544(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=544,
        )

    @property
    def on_545(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=545,
        )

    @property
    def on_546(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=546,
        )

    @property
    def on_547(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=547,
        )

    @property
    def on_548(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=548,
        )

    @property
    def on_549(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=549,
        )

    @property
    def on_550(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=550,
        )

    @property
    def on_551(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=551,
        )

    @property
    def on_552(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=552,
        )

    @property
    def on_553(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=553,
        )

    @property
    def on_554(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=554,
        )

    @property
    def on_555(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=555,
        )

    @property
    def on_556(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=556,
        )

    @property
    def on_557(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=557,
        )

    @property
    def on_558(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=558,
        )

    @property
    def on_559(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=559,
        )

    @property
    def on_560(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=560,
        )

    @property
    def on_561(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=561,
        )

    @property
    def on_562(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=562,
        )

    @property
    def on_563(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=563,
        )

    @property
    def on_564(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=564,
        )

    @property
    def on_565(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=565,
        )

    @property
    def on_566(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=566,
        )

    @property
    def on_567(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=567,
        )

    @property
    def on_568(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=568,
        )

    @property
    def on_569(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=569,
        )

    @property
    def on_570(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=570,
        )

    @property
    def on_571(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=571,
        )

    @property
    def on_572(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=572,
        )

    @property
    def on_573(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=573,
        )

    @property
    def on_574(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=574,
        )

    @property
    def on_575(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=575,
        )

    @property
    def on_576(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=576,
        )

    @property
    def on_577(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=577,
        )

    @property
    def on_578(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=578,
        )

    @property
    def on_579(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=579,
        )

    @property
    def on_580(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=580,
        )

    @property
    def on_581(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=581,
        )

    @property
    def on_582(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=582,
        )

    @property
    def on_583(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=583,
        )

    @property
    def on_584(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=584,
        )

    @property
    def on_585(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=585,
        )

    @property
    def on_586(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=586,
        )

    @property
    def on_587(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=587,
        )

    @property
    def on_588(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=588,
        )

    @property
    def on_589(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=589,
        )

    @property
    def on_590(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=590,
        )

    @property
    def on_591(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=591,
        )

    @property
    def on_592(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=592,
        )

    @property
    def on_593(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=593,
        )

    @property
    def on_594(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=594,
        )

    @property
    def on_595(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=595,
        )

    @property
    def on_596(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=596,
        )

    @property
    def on_597(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=597,
        )

    @property
    def on_598(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=598,
        )

    @property
    def on_599(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=599,
        )

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: (
                c
                not in [
                    100,
                    101,
                    102,
                    103,
                    104,
                    105,
                    106,
                    107,
                    108,
                    109,
                    110,
                    111,
                    112,
                    113,
                    114,
                    115,
                    116,
                    117,
                    118,
                    119,
                    120,
                    121,
                    122,
                    123,
                    124,
                    125,
                    126,
                    127,
                    128,
                    129,
                    130,
                    131,
                    132,
                    133,
                    134,
                    135,
                    136,
                    137,
                    138,
                    139,
                    140,
                    141,
                    142,
                    143,
                    144,
                    145,
                    146,
                    147,
                    148,
                    149,
                    150,
                    151,
                    152,
                    153,
                    154,
                    155,
                    156,
                    157,
                    158,
                    159,
                    160,
                    161,
                    162,
                    163,
                    164,
                    165,
                    166,
                    167,
                    168,
                    169,
                    170,
                    171,
                    172,
                    173,
                    174,
                    175,
                    176,
                    177,
                    178,
                    179,
                    180,
                    181,
                    182,
                    183,
                    184,
                    185,
                    186,
                    187,
                    188,
                    189,
                    190,
                    191,
                    192,
                    193,
                    194,
                    195,
                    196,
                    197,
                    198,
                    199,
                    200,
                    201,
                    202,
                    203,
                    204,
                    205,
                    206,
                    207,
                    208,
                    209,
                    210,
                    211,
                    212,
                    213,
                    214,
                    215,
                    216,
                    217,
                    218,
                    219,
                    220,
                    221,
                    222,
                    223,
                    224,
                    225,
                    226,
                    227,
                    228,
                    229,
                    230,
                    231,
                    232,
                    233,
                    234,
                    235,
                    236,
                    237,
                    238,
                    239,
                    240,
                    241,
                    242,
                    243,
                    244,
                    245,
                    246,
                    247,
                    248,
                    249,
                    250,
                    251,
                    252,
                    253,
                    254,
                    255,
                    256,
                    257,
                    258,
                    259,
                    260,
                    261,
                    262,
                    263,
                    264,
                    265,
                    266,
                    267,
                    268,
                    269,
                    270,
                    271,
                    272,
                    273,
                    274,
                    275,
                    276,
                    277,
                    278,
                    279,
                    280,
                    281,
                    282,
                    283,
                    284,
                    285,
                    286,
                    287,
                    288,
                    289,
                    290,
                    291,
                    292,
                    293,
                    294,
                    295,
                    296,
                    297,
                    298,
                    299,
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
                    400,
                    401,
                    402,
                    403,
                    404,
                    405,
                    406,
                    407,
                    408,
                    409,
                    410,
                    411,
                    412,
                    413,
                    414,
                    415,
                    416,
                    417,
                    418,
                    419,
                    420,
                    421,
                    422,
                    423,
                    424,
                    425,
                    426,
                    427,
                    428,
                    429,
                    430,
                    431,
                    432,
                    433,
                    434,
                    435,
                    436,
                    437,
                    438,
                    439,
                    440,
                    441,
                    442,
                    443,
                    444,
                    445,
                    446,
                    447,
                    448,
                    449,
                    450,
                    451,
                    452,
                    453,
                    454,
                    455,
                    456,
                    457,
                    458,
                    459,
                    460,
                    461,
                    462,
                    463,
                    464,
                    465,
                    466,
                    467,
                    468,
                    469,
                    470,
                    471,
                    472,
                    473,
                    474,
                    475,
                    476,
                    477,
                    478,
                    479,
                    480,
                    481,
                    482,
                    483,
                    484,
                    485,
                    486,
                    487,
                    488,
                    489,
                    490,
                    491,
                    492,
                    493,
                    494,
                    495,
                    496,
                    497,
                    498,
                    499,
                    500,
                    501,
                    502,
                    503,
                    504,
                    505,
                    506,
                    507,
                    508,
                    509,
                    510,
                    511,
                    512,
                    513,
                    514,
                    515,
                    516,
                    517,
                    518,
                    519,
                    520,
                    521,
                    522,
                    523,
                    524,
                    525,
                    526,
                    527,
                    528,
                    529,
                    530,
                    531,
                    532,
                    533,
                    534,
                    535,
                    536,
                    537,
                    538,
                    539,
                    540,
                    541,
                    542,
                    543,
                    544,
                    545,
                    546,
                    547,
                    548,
                    549,
                    550,
                    551,
                    552,
                    553,
                    554,
                    555,
                    556,
                    557,
                    558,
                    559,
                    560,
                    561,
                    562,
                    563,
                    564,
                    565,
                    566,
                    567,
                    568,
                    569,
                    570,
                    571,
                    572,
                    573,
                    574,
                    575,
                    576,
                    577,
                    578,
                    579,
                    580,
                    581,
                    582,
                    583,
                    584,
                    585,
                    586,
                    587,
                    588,
                    589,
                    590,
                    591,
                    592,
                    593,
                    594,
                    595,
                    596,
                    597,
                    598,
                    599,
                ]
            ),
            media_type="application/problem+json",
            expected_type=ErrorModel,
        )
