"""Version-specific OpenAPI reference types for v3.0 and v3.1.

This module re-exports versioned class aliases from openapi_pydantic to avoid
circular imports and provide a single canonical import site for version-specific
OpenAPI model classes used throughout the codebase.

Classes from v3.0 (openapi_pydantic.v3.v3_0):
    - OpenAPI30: OpenAPI 3.0 specification root
    - Parameter30: Parameter object for 3.0
    - RequestBody30: RequestBody object for 3.0
    - Response30: Response object for 3.0
    - Reference30: Reference object for 3.0

Classes from v3.1 (openapi_pydantic.v3.v3_1):
    - OpenAPI31: OpenAPI 3.1 specification root
    - Parameter31: Parameter object for 3.1
    - RequestBody31: RequestBody object for 3.1
    - Response31: Response object for 3.1
    - Reference31: Reference object for 3.1
"""

from __future__ import annotations

from openapi_pydantic.v3.v3_0 import (
    OpenAPI as OpenAPI30,
    Parameter as Parameter30,
    Reference as Reference30,
    RequestBody as RequestBody30,
    Response as Response30,
)
from openapi_pydantic.v3.v3_1 import (
    OpenAPI as OpenAPI31,
    Parameter as Parameter31,
    Reference as Reference31,
    RequestBody as RequestBody31,
    Response as Response31,
)

__all__ = [
    "OpenAPI30",
    "OpenAPI31",
    "Parameter30",
    "Parameter31",
    "RequestBody30",
    "RequestBody31",
    "Response30",
    "Response31",
    "Reference30",
    "Reference31",
]
