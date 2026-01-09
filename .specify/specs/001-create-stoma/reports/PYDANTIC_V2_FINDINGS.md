# Pydantic v2 自定义参数标记实现方案

## 问题分析

### 当前问题

在 Pydantic v2 中，当 `Param` 类继承自 `FieldInfo` 并在 `Annotated` 中使用时，自定义属性（如 `in_`）会丢失：

```python
from typing import Annotated
from pydantic import BaseModel
from src.params import Query  # Query 继承自 Param，Param 继承自 FieldInfo

class Test(BaseModel):
    limit: Annotated[int, Query()] = 20

# 问题：field_info.in_ 属性丢失
field_info = Test.model_fields['limit']
# field_info 是普通的 FieldInfo，不再是 Query 实例
# field_info.metadata 为空列表
```

### 根本原因

Pydantic v2 的字段处理机制：

1. **FieldInfo 提取与合并**：当 Pydantic 在 `Annotated` 中发现 `FieldInfo` 子类时，会提取它并与默认值赋值进行合并，创建一个新的 `FieldInfo` 对象
2. **自定义属性不被保留**：合并过程只保留 Pydantic 标准的 `FieldInfo` 属性（default、alias、description 等）
3. **非 FieldInfo 元数据被保留**：不继承自 `FieldInfo` 的对象会保留在 `metadata` 列表中

### FastAPI 的处理方式

FastAPI 的 `Query/Path/Header/Body` **确实**继承自 `FieldInfo`，但能正常工作是因为：

- FastAPI 不直接在 Pydantic 模型中使用这些对象
- FastAPI 在**依赖注入阶段**提取参数信息，早于 Pydantic 处理模型
- 这些对象由 FastAPI 的依赖系统解析，不由 Pydantic 解析

## 解决方案

### 方案对比

我们的场景是在 Pydantic `BaseModel` 类（`APIRoute`）中直接使用 `Param` 对象，有两个方案：

**方案 1：不继承 FieldInfo**（推荐）
- 创建简单的标记类，不继承 `FieldInfo`
- 存储在 `Annotated` 元数据中，Pydantic 会保留它们
- 使用标准 `Field()` 单独处理验证约束

**方案 2：混合方法**
- 保持 `Param` 继承 `FieldInfo` 用于验证
- 在 `Annotated` 中添加单独的标记类用于 `in_` 属性

### 推荐实现：方案 1

#### 实现思路

1. **参数标记类**：创建简单的数据类，存储参数类型和元数据
2. **验证约束**：使用 Pydantic 标准的 `Field()` 处理验证
3. **元数据提取**：在 `_collect_params()` 中从 `field_info.metadata` 提取标记对象

#### 代码结构

```python
# src/params.py
from dataclasses import dataclass
from enum import Enum
from typing import Any

class ParamTypes(Enum):
    query = "query"
    header = "header"
    path = "path"
    body = "body"

@dataclass(frozen=True)
class ParamMarker:
    """参数标记基类，用于在 Annotated 中标记参数类型。
    
    不继承 FieldInfo，因此会被 Pydantic 保留在 metadata 中。
    """
    in_: ParamTypes
    # 存储 FastAPI 特定的元数据
    include_in_schema: bool = True
    deprecated: bool | None = None
    example: Any = None
    examples: list[Any] | None = None
    openapi_examples: dict[str, Any] | None = None

@dataclass(frozen=True)
class Query(ParamMarker):
    """查询参数标记。"""
    in_: ParamTypes = ParamTypes.query

@dataclass(frozen=True)
class Path(ParamMarker):
    """路径参数标记。"""
    in_: ParamTypes = ParamTypes.path

@dataclass(frozen=True)
class Header(ParamMarker):
    """请求头参数标记。"""
    in_: ParamTypes = ParamTypes.header
    convert_underscores: bool = True

@dataclass(frozen=True)
class Body(ParamMarker):
    """请求体参数标记。"""
    in_: ParamTypes = ParamTypes.body
    embed: bool = False
    media_type: str = "application/json"
```

#### 使用示例

```python
from typing import Annotated
from pydantic import Field
from src.params import Query, Path, Header, Body
from src.routing import APIRoute, APIRouter

router = APIRouter(servers=["https://api.example.com"])

@router.get("/users/{user_id}")
class GetUser(APIRoute[UserData]):
    # 参数类型标记
    user_id: Annotated[int, Path()] = ...  # 路径参数始终必需
    
    # 查询参数 + 验证约束
    limit: Annotated[int, Query(), Field(ge=1, le=100, description="分页大小")] = 20
    offset: Annotated[int, Query(), Field(ge=0, description="偏移量")] = 0
    
    # 请求头
    authorization: Annotated[str, Header(), Field(alias="Authorization")]
    
    # 请求体
    body: Annotated[UserUpdateData, Body()]
```

#### 优势

1. **清晰分离**：参数类型标记和验证约束分离
2. **Pydantic 原生支持**：充分利用 `Field()` 的所有功能
3. **元数据保留**：自定义属性不会丢失
4. **类型安全**：使用 dataclass 确保类型检查

## 实现计划

### 需要修改的文件

1. **src/params.py**
   - 将 `Param` 从 `FieldInfo` 改为简单的 `dataclass`
   - 移除验证相关参数（由 `Field()` 处理）
   - 保留 FastAPI 特定的元数据字段

2. **src/routing.py**
   - 更新 `_get_param_info()` 从 `metadata` 中提取 `ParamMarker`
   - 更新 `_get_param_name()` 从 `Field` 的 `alias` 获取别名

3. **tests/unit/test_params.py**
   - 更新测试用例以适配新的 API

### 兼容性注意事项

这是一个破坏性变更：

**变更前**：
```python
limit: Annotated[int, Query(ge=1, le=100, description="limit")] = 20
```

**变更后**：
```python
limit: Annotated[int, Query(), Field(ge=1, le=100, description="limit")] = 20
```

## 参考资料

- [Pydantic v2 Fields Documentation](https://docs.pydantic.dev/latest/concepts/fields/)
- [Pydantic v2 Annotated Pattern](https://docs.pydantic.dev/latest/concepts/fields/#the-annotated-pattern)
- [Pydantic v2 Custom Types](https://docs.pydantic.dev/latest/concepts/types/#custom-types)
- [FastAPI params.py Source](https://github.com/tiangolo/fastapi/blob/master/fastapi/params.py)
