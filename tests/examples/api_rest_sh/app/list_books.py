from __future__ import annotations

from stoma import APIRouter, APIRoute
from .models import ListBooksResponse, ErrorModel

router = APIRouter()


@router.get("/books")
class ListBooks(APIRoute[ListBooksResponse | ErrorModel]):
    pass
