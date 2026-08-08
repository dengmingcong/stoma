"""Type definitions for openapi models.

This file exists to avoid circular import issues between models.py and
parser.py/renderer.py. SpecVersion is used by both sides, so it lives here
in its own minimal module to break the import cycle.
"""
from __future__ import annotations

from typing import Literal

SpecVersion = Literal["3.0", "3.1"]
