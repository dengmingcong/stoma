"""Deletes a pet.。

Generated from OpenAPI: deletePet
Delete a pet.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from stoma import APIRoute, APIRouter, Header

router = APIRouter()


@router.delete("/pet/{petId}")
class DeletePet(APIRoute):
    """Deletes a pet.。

    Delete a pet.
    """

    pet_id: Annotated[int, Field(serialization_alias="petId")]
    """Pet id to delete"""
    api_key: Annotated[str | None, Header()] = None
