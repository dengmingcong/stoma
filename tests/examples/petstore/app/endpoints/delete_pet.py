"""Deletes a pet.。

Generated from OpenAPI: deletePet
Delete a pet.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from stoma import APIRoute, EmptyResponseSpec, Header

from ..router import router


@router.delete("/pet/{petId}")
class DeletePet(APIRoute):
    """Deletes a pet.。

    Delete a pet.
    """

    pet_id: Annotated[int, Field(serialization_alias="petId")]
    """Pet id to delete"""
    api_key: Annotated[str | None, Header()] = None

    @property
    def on_200(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=200,
        )

    @property
    def on_400(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=400,
        )

    @property
    def on_default(self) -> EmptyResponseSpec:
        return EmptyResponseSpec(
            status_code=lambda c: c not in [200, 400],
        )
