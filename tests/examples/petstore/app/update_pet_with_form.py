"""Updates a pet in the store with form data.。

Generated from OpenAPI: updatePetWithForm
Updates a pet resource based on the form data.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from stoma import APIRoute, APIRouter

from .models import Pet

router = APIRouter()


@router.post("/pet/{petId}")
class UpdatePetWithForm(APIRoute[Pet]):
    """Updates a pet in the store with form data.。

    Updates a pet resource based on the form data.
    """

    pet_id: Annotated[int, Field(serialization_alias="petId")]
    """ID of pet that needs to be updated"""
    name: str | None = None
    """Name of pet that needs to be updated"""
    status: str | None = None
    """Status of pet that needs to be updated"""
