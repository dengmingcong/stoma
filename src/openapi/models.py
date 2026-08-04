"""OpenAPI 生成器的中间表示（IR）模型。"""

from openapi_pydantic.v3.v3_0 import (
    Parameter as Parameter30,
)
from openapi_pydantic.v3.v3_0 import (
    RequestBody as RequestBody30,
)
from openapi_pydantic.v3.v3_0 import (
    Response as Response30,
)
from openapi_pydantic.v3.v3_1 import (
    Parameter as Parameter31,
)
from openapi_pydantic.v3.v3_1 import (
    RequestBody as RequestBody31,
)
from openapi_pydantic.v3.v3_1 import (
    Response as Response31,
)
from pydantic import BaseModel

# 支持 OpenAPI 3.0.x 和 3.1.x
Parameter = Parameter30 | Parameter31
RequestBody = RequestBody30 | RequestBody31
Response = Response30 | Response31


class Endpoint(BaseModel):
    """单个接口的完整信息（IR - Intermediate Representation）。"""

    operation_id: str
    method: str
    path: str
    summary: str | None
    description: str | None
    parameters: list[Parameter]
    request_body: RequestBody | None
    responses: dict[str, Response] | None
