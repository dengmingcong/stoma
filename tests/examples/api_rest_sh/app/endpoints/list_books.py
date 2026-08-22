from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, ListBooksResponse
from ..router import router


@router.get("/books")
class ListBooks(APIRoute):
    @property
    def on_200(self) -> JSONResponseSpec[ListBooksResponse]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=ListBooksResponse)

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
