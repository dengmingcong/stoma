"""路由相关的核心类型和装饰器。

此模块提供了类似 FastAPI 风格的路由定义能力，包括：

- RouteMeta：不可变的路由元数据类。
- APIRoute：接口基类（待实现）。
- APIRouter：路由装饰器提供者（待实现）。
"""

from pydantic import BaseModel, ConfigDict


class RouteMeta(BaseModel):
    """路由元数据，不可变。

    用于存储接口的 HTTP 方法和路径信息，通过装饰器注入到接口类中。

    :var method: HTTP 方法（GET、POST、PUT、PATCH、DELETE 等）。
    :vartype method: str
    :var path: 接口路径，支持路径参数占位符（如 /users/{user_id}）。
    :vartype path: str

    Example::

        meta = RouteMeta(method="GET", path="/users/{user_id}")
        print(meta.method)  # GET
        print(meta.path)    # /users/{user_id}
    """

    model_config = ConfigDict(frozen=True)

    method: str
    path: str
