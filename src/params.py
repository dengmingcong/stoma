"""参数标记类型，参考 FastAPI 的实现方式。

此模块提供了用于标记接口参数来源的类型，包括：

- Query：查询参数
- Path：路径参数
- Header：请求头参数
- Body：请求体参数

这些类型只是标记，用于区分参数来源，不继承任何 Pydantic 类。
其他属性（如 alias、ge、le 等）使用 Pydantic 原生 ``Field()`` 设置。
"""

import pathlib
from dataclasses import dataclass
from enum import Enum


class ParamTypes(Enum):
    """参数类型枚举。

    stoma 不处理 cookie 参数：cookie 值由用户在创建 Playwright APIRequestContext 时通过
    ``storage_state={"cookies": [...]}`` 注入，Playwright 会自动随请求发送。
    """

    query = "query"
    header = "header"
    path = "path"
    body = "body"


class Param:
    """参数标记基类。

    只用于标记参数来源（query/header/path/body），不保存其他属性。
    其他属性使用 Pydantic ``Field()`` 设置。

    FastAPI 的 Param 之所以需要继承 FieldInfo，是因为 FastAPI 是以函数的形式定义接口的，
    而我们是以类的形式定义接口的并且继承了 pydantic BaseModel，所以不需要继承 FieldInfo。
    这样更简单，而且可以直接使用 Pydantic 的 Field() 来设置其他属性。

    Example::

        # ✅ 推荐写法（FastAPI 官方示例）：metadata 全部放进 ``Annotated[...]``
        authorization: Annotated[str, Header(), Field(serialization_alias="Authorization")]

        # ✅ 兼容写法（旧代码示例）：``Field()`` 放在 ``=`` 右侧，Pydantic v2 同样支持
        authorization: Annotated[str, Header()] = Field(alias="Authorization")
    """

    in_: ParamTypes


class Path(Param):
    """路径参数标记。

    用于标记接口类中的路径参数字段。路径参数必须在路径模板中定义（如 /users/{user_id}）。

    Example::

        # ✅ 推荐写法：``Annotated[T, Path()]``
        user_id: Annotated[int, Path()]

        # ✅ 兼容写法：``Annotated[T, Path()] = Field(...)``
        user_id: Annotated[int, Path()] = Field(ge=1)
    """

    in_ = ParamTypes.path


class Query(Param):
    """查询参数标记。

    用于标记接口类中的查询参数字段。查询参数会附加在 URL 后面（如 ?limit=10）。

    Example::

        # ✅ 推荐写法：``Annotated[T, Query(), Field(...)]``
        limit: Annotated[int, Query(), Field(ge=1, le=100)]

        # ✅ 兼容写法：``Annotated[T, Query()] = Field(...)``
        limit: Annotated[int, Query()] = Field(ge=1, le=100)
    """

    in_ = ParamTypes.query


class Header(Param):
    """请求头参数标记。

    用于标记接口类中的请求头字段。请求头参数会从 HTTP 请求头中提取。

    Example::

        # ✅ 推荐写法：``Annotated[T, Header(), Field(serialization_alias=...)]``
        authorization: Annotated[str, Header(), Field(serialization_alias="Authorization")]

        # ✅ 兼容写法：``Annotated[T, Header()] = Field(alias=...)``
        authorization: Annotated[str, Header()] = Field(alias="Authorization")
    """

    in_ = ParamTypes.header


class Body(Param):
    """请求体参数标记。

    用于标记接口类中的请求体字段。请求体会被序列化为 JSON 发送到服务器。

    :param embed: 是否嵌入单个字段。default: False

    Example::

        class UserCreateRequest(BaseModel):
            name: str
            email: str

        # ✅ 推荐写法：``Annotated[T, Body()]``
        body: Annotated[UserCreateRequest, Body()]
        data: Annotated[User, Body(embed=True)]

        # ✅ 兼容写法：``Annotated[T, Body()] = Field(...)``
        body: Annotated[UserCreateRequest, Body()] = Field(description="请求体")
    """

    in_ = ParamTypes.body

    def __init__(self, embed: bool = False) -> None:
        """初始化 Body 标记。

        :param embed: 是否嵌入单个字段。
        """
        self.embed = embed


class Form(Body):
    """表单参数标记。

    用于标记接口类中的表单字段。表单数据会被编码后发送到服务器。
    """

    in_ = ParamTypes.body

    def __init__(self) -> None:
        pass


@dataclass
class UploadFile:
    """上传文件标记。

    用于标记接口类中的文件上传字段。

    :var path: 上传文件的本地路径。
    """

    path: pathlib.Path


__all__ = ["Param", "ParamTypes", "Query", "Path", "Header", "Body", "Form", "UploadFile"]
