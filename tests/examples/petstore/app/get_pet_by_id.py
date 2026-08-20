"""Find pet by ID.。

Generated from OpenAPI: getPetById
Returns a single pet.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from stoma import APIRoute, APIRouter

from .models import Pet

router = APIRouter()


@router.get("/pet/{petId}")
class GetPetById(APIRoute[Pet]):
    """Find pet by ID.。

    Returns a single pet.
    """

    pet_id: Annotated[int, Field(serialization_alias="petId")]
    """ID of pet to return"""
