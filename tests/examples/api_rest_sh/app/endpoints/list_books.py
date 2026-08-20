from __future__ import annotations

from stoma import APIRoute

from ..models import ErrorModel, ListBooksResponse
from ..router import router


@router.get("/books")
class ListBooks(APIRoute[ListBooksResponse | ErrorModel]):
    pass
