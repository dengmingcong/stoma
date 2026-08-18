"""list-books。

Generated from OpenAPI: list-books
"""

from __future__ import annotations

from .models import ListBooksResponse, ErrorModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/books")
class ListBooks(APIRoute[ListBooksResponse | ErrorModel]):
    """list-books。"""
