"""OpenAPI 模块的固定常量定义。

集中存放：

- :data:`SpecVersion`：支持的 OpenAPI 主版本（``3.0`` / ``3.1``），由 parser
  与 renderer 共用，独立成模块以避免循环 import。
- 版本特定的 Pydantic 模型类别名（``OpenAPI30/31``、``Parameter30/31``、
  ``RequestBody30/31``、``Response30/31``、``Reference30/31``）：从
  ``openapi_pydantic`` 重新导出，供 parser 与 renderer 按版本注入使用。

将这些不变的定义集中在一处，使 parser / renderer / models 能单向依赖本模块，
避免双向耦合。
"""

from __future__ import annotations

from typing import Literal

from openapi_pydantic.v3.v3_0 import (
    OpenAPI as OpenAPI30,
)
from openapi_pydantic.v3.v3_0 import (
    Parameter as Parameter30,
)
from openapi_pydantic.v3.v3_0 import (
    Reference as Reference30,
)
from openapi_pydantic.v3.v3_0 import (
    RequestBody as RequestBody30,
)
from openapi_pydantic.v3.v3_0 import (
    Response as Response30,
)
from openapi_pydantic.v3.v3_1 import (
    OpenAPI as OpenAPI31,
)
from openapi_pydantic.v3.v3_1 import (
    Parameter as Parameter31,
)
from openapi_pydantic.v3.v3_1 import (
    Reference as Reference31,
)
from openapi_pydantic.v3.v3_1 import (
    RequestBody as RequestBody31,
)
from openapi_pydantic.v3.v3_1 import (
    Response as Response31,
)

SpecVersion = Literal["3.0", "3.1"]

__all__ = [
    "OpenAPI30",
    "OpenAPI31",
    "Parameter30",
    "Parameter31",
    "Reference30",
    "Reference31",
    "RequestBody30",
    "RequestBody31",
    "Response30",
    "Response31",
    "SpecVersion",
]
