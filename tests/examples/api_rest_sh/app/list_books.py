from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import ErrorModel, ListBooksResponse

router = APIRouter()


@router.get("/books")
class ListBooks(APIRoute[ListBooksResponse | ErrorModel]):
    pass
