"""Finds Pets by status.。

Generated from OpenAPI: findPetsByStatus
Multiple status values can be provided with comma separated strings.
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import FindPetsByStatusResponse
from ..router import router


@router.get("/pet/findByStatus")
class FindPetsByStatus(APIRoute[FindPetsByStatusResponse]):
    """Finds Pets by status.。

    Multiple status values can be provided with comma separated strings.
    """

    status: str
    """Status values that need to be considered for filter"""
