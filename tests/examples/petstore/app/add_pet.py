"""Add a new pet to the store.。

Generated from OpenAPI: addPet
Add a new pet to the store.
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import Pet

router = APIRouter()


@router.post("/pet")
class AddPet(APIRoute[Pet]):
    """Add a new pet to the store.。

    Add a new pet to the store.
    """

    body: Pet
