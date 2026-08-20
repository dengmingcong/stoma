"""Update an existing pet.。

Generated from OpenAPI: updatePet
Update an existing pet by Id.
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import Pet
from ..router import router


@router.put("/pet")
class UpdatePet(APIRoute[Pet]):
    """Update an existing pet.。

    Update an existing pet by Id.
    """

    body: Pet
