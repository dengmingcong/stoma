from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel, ListBooksResponse
from ..router import router


@router.get("/books")
class ListBooks(APIRoute):
    @property
    def on_200(self) -> ResponseSpec[ListBooksResponse]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=ListBooksResponse)

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", expected_type=ErrorModel
        )
