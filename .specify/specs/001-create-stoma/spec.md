# 功能规范：接口自动化测试框架 Stoma（仿 FastAPI 声明式定义）

**功能分支**: `001-create-stoma`  
**创建时间**: 2025-12-12  
**状态**: 草稿  
**输入**: 用户描述: "创建一个接口自动化测试框架，借鉴 fastapi 定义接口的方式，使用 pydantic 作为类型检查和序列化，但实际并不将 fastapi 作为依赖"

## 用户场景与测试（必填）

### 用户故事 1 - 从 OpenAPI 生成类型化接口定义（优先级：P1）

测试工程师或开发者希望从 OpenAPI Specification 预生成出类型化的接口定义。每个接口表示为一个**可调用的类**，其构造函数接收接口所需的全部参数（path 参数、查询参数、header 参数、request body），通过参数的类型注解和默认值，调用方能清晰地了解需要传入哪些参数、参数类型以及可选性。类的其他方法负责调用实际的 HTTP 接口并将响应按照生成的模型进行组装与校验。

**为何优先**: 这是核心价值主张，决定框架的易用性与采用成本。生成代码的质量（清晰度、类型安全、可维护性）直接影响测试脚本的编写效率。

**独立测试**: 通过在空白项目中导入生成的接口类，仅通过类型提示和参数传递，即可完整理解接口的请求与响应结构；无需查阅 OpenAPI 文档或其他辅助信息。

**验收场景**:

1. Given 用户从 OpenAPI 生成接口定义，When 在 IDE 中查看生成的接口类，Then 类的构造函数签名明确列出所有参数及其类型/可选性，使用者可直接进行代码补全与静态类型检查。
2. Given 接口包含 path/query/header/body 参数混合，When 实例化接口类，Then 构造函数强制规范参数来源（Query/Body/Header/Path 标记），防止参数混淆。
3. Given 接口返回 JSON 对象，When 调用接口方法，Then 返回结果自动按照生成的响应模型进行类型校验和反序列化，确保类型安全。

**伪代码示例**（生成的接口类）：

```python
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

# 框架提供的基类（所有生成的接口类都继承此类）
class BaseEndpoint(Generic[T]):
    """接口基类，通过泛型指定响应模型类型"""
    
    async def call(self) -> T:
        """
        通用 call 方法（由框架基类实现）：
        1. 从实例属性自动收集请求参数（query/path/header/body）
        2. 使用 Playwright 发送 HTTP 请求
        3. 将响应 JSON 自动解析为泛型类型 T 的实例
        """
        # 框架内部实现：参数收集 -> HTTP 调用 -> 响应解析


# ===== 以下是生成的代码 =====

# 生成的响应模型
class UserData(BaseModel):
    id: int
    name: str
    email: str

class UserCreateRequest(BaseModel):
    name: str
    email: str

# 生成的接口类：通过泛型参数明确响应类型
class GetUsersEndpoint(BaseEndpoint[list[UserData]]):
    """GET /users - 列出用户（响应类型：list[UserData]）"""
    
    def __init__(
        self,
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        token: str = Header(alias="Authorization"),
    ):
        """
        参数说明：
        - limit (Query): 返回结果数量，默认 20
        - offset (Query): 分页偏移，默认 0
        - token (Header): 认证令牌，来自 Authorization header
        """
        self.limit = limit
        self.offset = offset
        self.token = token
    # 无需定义 call() 方法，继承自 BaseEndpoint


class CreateUserEndpoint(BaseEndpoint[UserData]):
    """POST /users - 创建用户（响应类型：UserData）"""
    
    def __init__(
        self,
        body: UserCreateRequest = Body(...),
        idempotency_key: str = Header(default=None, alias="Idempotency-Key"),
    ):
        """
        参数说明：
        - body (Body): 请求体，包含 name、email 等字段
        - idempotency_key (Header): 幂等性密钥，可选
        """
        self.body = body
        self.idempotency_key = idempotency_key


class GetUserByIdEndpoint(BaseEndpoint[UserData]):
    """GET /users/{user_id} - 获取特定用户（响应类型：UserData）"""
    
    def __init__(
        self,
        user_id: int = Path(...),
        include_profile: bool = Query(default=False),
    ):
        """
        参数说明：
        - user_id (Path): 路径参数，用户 ID
        - include_profile (Query): 是否包含用户详细信息，默认 False
        """
        self.user_id = user_id
        self.include_profile = include_profile
```

**使用示例**：

```python
# 测试脚本中的使用
from users.endpoints import GetUsersEndpoint, CreateUserEndpoint, GetUserByIdEndpoint
from users.models import UserCreateRequest, UserData

# 1. 列出用户（使用默认参数）
list_endpoint = GetUsersEndpoint(token="Bearer xxx")
users = await list_endpoint.call()  # 返回 list[UserData]

# 2. 创建用户
create_endpoint = CreateUserEndpoint(
    body=UserCreateRequest(name="Alice", email="alice@example.com"),
    idempotency_key="unique-key-123"
)
new_user = await create_endpoint.call()  # 返回 UserData

# 3. 获取特定用户
get_endpoint = GetUserByIdEndpoint(user_id=1, include_profile=True)
user_data = await get_endpoint.call()  # 返回 UserData
```

## 需求（必填）

### 功能性需求

- **FR-001**: 框架必须支持将 OpenAPI Specification 定义的 HTTP 接口直接转换为框架对接口的定义。
- **FR-002**: 框架必须提供声明式接口定义方式以描述请求与响应。
- **FR-003**: 框架必须基于 Pydantic 对请求构造与响应解析进行类型校验与序列化/反序列化。
- **FR-004**: 框架必须生成可读的测试报告（含通过/失败统计、失败原因、差异对比、输入摘要）。
- **FR-005**: 框架不得依赖 FastAPI，但允许“受其启发”的声明风格与注解设计。命名策略采用常见动词注解与参数标识：支持 `@get`, `@post`, `@put`, `@patch`, `@delete` 以及参数来源标记 `Query`, `Body`, `Header`, `Path`，并在文档中明确说明“本框架与 FastAPI 无依赖关系，仅保留通用语义命名”。
- **FR-006**: 框架必须使用 Playwright 作为接口请求的客户端。
- **FR-007**: 框架必须提供 CLI 工具,从 OpenAPI 规范文件预先生成 Python 请求/响应模型与端点定义代码,测试运行阶段仅加载生成代码而不再解析 OpenAPI 文件。
- **FR-008**: 生成产物的目录结构必须按 feature 维度归档,每个功能一个包,至少包含 `router.py`(汇总该功能所有接口) 与 `models.py`(该功能所有接口相关模型);允许在包内扩展如 `schemas.py`, `utils.py` 等,整体参考 fastapi-best-practices 的组织方式,以提升可维护性与可发现性。
- **FR-009**: 提供命令行入口 `stoma make`,最小必需参数包括 `--spec <openapi.yaml>`、`--out <dir>`、`--feature <name>`; 其中 `--feature` 用于将同一业务域的接口与模型归档到同一包(例如 `users/`),命令执行后在输出目录按 `feature` 生成包含 `router.py` 与 `models.py` 的包结构。

### 关键实体

- **接口定义（Endpoint）**: 名称、方法、路径、请求模型、响应模型。
- **请求模型（Request）**: 字段、必填/可选、默认值、校验规则、示例数据。
- **响应模型（Response）**: 字段、类型、可选/严格策略、容错策略。

## 成功标准（必填）

### 可度量结果

- **SC-001**: 新用户在 5 分钟内可完成从安装到将 OpenAPI Specification 定义转换为框架对接口的定义。

### 假设

- 默认目标为 HTTP 接口测试；非 HTTP 场景可通过用户自定义适配器扩展。
- 使用 Pydantic v2 语义进行类型定义与校验；若版本差异，需提供兼容指引。
- 报告以文件或控制台输出为主；可选集成到外部平台不在本规范范围内。

### 需澄清事项（最多 3 项）

- 命名/注解可借鉴范围：采用保留常见动词注解（get/post 等）与参数标识（Query/Body 等）的策略，且在文档中声明无 FastAPI 依赖，仅为通用约定，减少迁移成本。
- 报告形式：内置 HTML 报告文件输出（同时保留控制台摘要），以便分享与归档；HTML 报告至少包含套件统计、用例明细、失败差异对比与输入摘要。
- 框架的作用过程可以看作 FastAPI 的反面。FastAPI 是通过模型生成 OpenAPI Specification，框架是从 OpenAPI Specification 生成模型。
	- 决策补充：采用“预先代码生成”工作流，通过 CLI 将 OpenAPI 转换为静态 Python 模型与端点定义，提升运行性能与类型安全；运行阶段不再进行动态解析。

## Clarifications

### Session 2025-12-15

- Q: OpenAPI Specification 的转换是运行时动态生成还是预先代码生成? → A: 预先代码生成
- Q: 代码生成产物的输出结构应如何组织? → A: 按 feature 归档的包结构,参考 fastapi-best-practices: 每个功能一个包,`router.py` 存放该功能所有接口,`models.py` 存放该功能所有接口相关模型,其余辅助文件同包内组织。
- Q: 代码生成 CLI 的入口命令与最小参数集合? → A: 使用 `stoma make --spec <openapi.yaml> --out <dir> --feature <name>` 形式。

### Session 2025-12-16

- Q: 响应模型的类型注解位置与可见性（基于类的接口设计中，如何在保持 call() 方法通用的前提下明确响应类型）? → A: 采用 Python 泛型（Generic）方案。生成的接口类继承 `BaseEndpoint[T]`，通过泛型参数明确响应类型（如 `BaseEndpoint[list[UserData]]`），既保证 IDE/mypy 可正确推断 `call()` 返回类型，又让响应模型在类定义处一目了然。子类无需定义 call() 方法，完全继承基类的通用实现。
