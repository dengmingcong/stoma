# 功能规范：接口自动化测试框架 Stoma（仿 FastAPI 声明式定义）

**功能分支**: `001-create-stoma`  
**创建时间**: 2025-12-12  
**状态**: 草稿  
**输入**: 用户描述: "创建一个接口自动化测试框架，借鉴 fastapi 定义接口的方式，使用 pydantic 作为类型检查和序列化，但实际并不将 fastapi 作为依赖"

## 用户场景与测试（必填）

### 用户故事 1 - 确定类型化接口定义格式（优先级：P0）

测试工程师或开发者需要一种清晰、类型安全的接口定义格式。每个接口表示为一个**可调用的类**，其构造函数接收接口所需的全部参数（path 参数、查询参数、header 参数、request body），通过参数的类型注解和默认值明确参数类型与可选性。接口类使用装饰器（如 `@router.get`）声明 HTTP 方法和路径，并通过泛型指定响应模型类型。

**为何优先**: 这是框架的基础定义，所有后续功能（代码生成、HTTP 调用）都依赖此接口格式。必须在实现任何功能前先确定接口定义的结构与约束。

**独立测试**: 通过编写示例接口类（手动编写，不依赖生成），验证类型注解、IDE 提示、装饰器语法的可用性与一致性。

**验收场景**:

1. Given 开发者手动编写接口类，When 使用 `@router.get/post` 装饰器传入 path，Then IDE 提供参数补全与类型检查。
2. Given 接口类继承 `APIRoute[T]` 泛型，When 调用实例（`endpoint()`），Then mypy/IDE 可正确推断返回类型为 T。
3. Given 接口类继承 BaseModel 并使用 Query/Body/Header/Path 标记，When 字段声明完成，Then IDE 自动补全所有字段，无需编写 `__init__` 样板代码。
4. Given 生成的接口类使用路由元数据隔离（`_route_meta`），When 用户字段名为 method、path 等，Then 不产生命名冲突，框架正常工作。

**伪代码示例**（接口定义格式）：

```python
from typing import ClassVar, Literal, Callable, Annotated
from pydantic import BaseModel, Field, ConfigDict

# ===== 框架核心定义 =====

class RouteMeta(BaseModel):
    """路由元数据（不可变），集中存储所有路由信息，避免与用户字段冲突"""
    model_config = ConfigDict(frozen=True)
    
    method: str
    path: str
    servers: list[str] | None = None  # 接口级别的服务器列表，优先级高于 APIRouter 的全局 servers


# Query、Header、Path、Body 将由代码生成器导入，框架此处仅声明类型
# （这些类型的具体实现将在后续版本实现）
# 【实现约束】Query/Body/Header/Path 类的内部实现代码必须参考 FastAPI 的实现方式，
# 确保行为一致性、参数验证逻辑、以及与 Pydantic 的集成方式遵循 FastAPI 的最佳实践。
Query: type  # 占位符，代码生成时会导入真实实现
Header: type  # 占位符，代码生成时会导入真实实现
Path: type  # 占位符，代码生成时会导入真实实现
Body: type  # 占位符，代码生成时会导入真实实现


# 框架提供的基类（继承 Pydantic BaseModel 以获得最佳 IDE 支持）
class APIRoute[T](BaseModel):
    """
    接口基类，通过泛型指定响应模型类型。
    
    设计特点：
    1. 继承 BaseModel：自动 __init__ 生成，参数 → 属性，无需样板代码
    2. 元数据隔离：所有路由信息存储在 _route_meta，避免与用户字段冲突
    3. IDE 支持：字段声明即完成一切，IDE 完美补全与类型检查
    """
    _route_meta: ClassVar[RouteMeta]
    
    def __call__(self) -> T:
        """
        通用 __call__ 方法（由框架基类实现）：
        1. 从实例字段自动收集请求参数（query/path/header/body）
        2. 使用 Playwright 发送 HTTP 请求
        3. 将响应 JSON 自动解析为泛型类型 T 的实例
        
        详细实现将在用户故事 2 中完成。
        
        注意：当前版本为同步实现，异步支持将在后续版本添加。
        """
        pass


def api_route_decorator[
    T: APIRoute
](
    *,
    method: Literal["GET","POST","PUT","PATCH","DELETE"],
    path: str,
    servers: list[str] | None = None,
) -> Callable[[type[T]], type[T]]:
    """
    类装饰器：在 class 声明处传入元数据。被装饰的类必须继承自 APIRoute。
    IDE 在此位置提供参数补全与类型检查。
    """
    def update_api_route(cls: type[T]) -> type[T]:
        cls._route_meta = RouteMeta(
            method=method,
            path=path,
            servers=servers
        )
        return cls
    return update_api_route


# 便捷路由命名空间：与 FastAPI 类似的入口 router.get/router.post 等
class APIRouter:
    """路由器，支持全局 servers 配置和接口级别的 servers 覆盖。"""
    
    def __init__(self, servers: list[str] | None = None):
        """初始化路由器，可指定全局服务器列表（如 OpenAPI servers）。"""
        self.servers = servers
    
    def get[T: APIRoute](self, path: str, *, servers: list[str] | None = None) -> Callable[[type[T]], type[T]]:
        return api_route_decorator(method="GET", path=path, servers=servers)

    def post[T: APIRoute](self, path: str, *, servers: list[str] | None = None) -> Callable[[type[T]], type[T]]:
        return api_route_decorator(method="POST", path=path, servers=servers)

    def put[T: APIRoute](self, path: str, *, servers: list[str] | None = None) -> Callable[[type[T]], type[T]]:
        return api_route_decorator(method="PUT", path=path, servers=servers)

    def patch[T: APIRoute](self, path: str, *, servers: list[str] | None = None) -> Callable[[type[T]], type[T]]:
        return api_route_decorator(method="PATCH", path=path, servers=servers)

    def delete[T: APIRoute](self, path: str, *, servers: list[str] | None = None) -> Callable[[type[T]], type[T]]:
        return api_route_decorator(method="DELETE", path=path, servers=servers)

# 创建全局路由器实例，可在代码生成时配置默认 servers
router = APIRouter(servers=["https://api.example.com"])

# ===== 以下是生成的代码 =====

# 生成的响应模型
class UserData(BaseModel):
    id: int
    name: str
    email: str

class UserCreateRequest(BaseModel):
    name: str
    email: str

# 生成的接口类：无需 __init__，继承 BaseModel 自动生成
@router.get("/users")
class GetUsers(APIRoute[list[UserData]]):
    """获取用户列表 - 响应类型：list[UserData]。"""
    
    limit: Annotated[int, Query(ge=1, le=100)] = 20
    offset: Annotated[int, Query(ge=0)] = 0
    token: Annotated[str, Header(alias="Authorization")]


@router.post("/users")
class CreateUser(APIRoute[UserData]):
    """创建用户 - 响应类型：UserData。"""
    
    body: Annotated[UserCreateRequest, Body()]
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None


@router.get("/users/{user_id}")
class GetUserById(APIRoute[UserData]):
    """获取特定用户 - 响应类型：UserData。"""
    
    user_id: Annotated[int, Path()]
    include_profile: Annotated[bool, Query()] = False
```

**使用示例**：

```python
# 测试脚本中的使用
from users.endpoints import GetUsers, CreateUser, GetUserById
from users.models import UserCreateRequest, UserData

# 1. 列出用户（使用默认参数）
list_endpoint = GetUsers(token="Bearer xxx")  # IDE 完美补全所有字段
users = list_endpoint()  # 类型推断: list[UserData]

# 2. 创建用户
create_endpoint = CreateUser(
    body=UserCreateRequest(name="Alice", email="alice@example.com"),
    idempotency_key="unique-key-123"
)
new_user = create_endpoint()  # 类型推断: UserData

# 3. 获取特定用户
get_endpoint = GetUserById(user_id=1, include_profile=True)
user_data = get_endpoint()  # 类型推断: UserData

# 4. 访问路由元数据（框架内部使用）
meta = GetUsers.route_meta()
print(meta.method)         # "GET"
print(meta.path)           # "/users"
```

### 用户故事 2 - 使用 Playwright 调用接口（优先级：P1）

测试工程师希望实例化接口类后，通过调用实例自动发送 HTTP 请求并获得类型化的响应。框架内部使用 Playwright 作为 HTTP 客户端，自动从实例属性收集请求参数（query/path/header/body），构造请求，发送到目标服务器，并将响应 JSON 解析为 Pydantic 响应模型。

**为何优先**: 这是框架的核心执行能力，验证接口定义可以真正调用远程服务并获得结果。

**独立测试**: 启动一个简单的 HTTP 测试服务器（如 FastAPI），手动编写接口类定义，调用接口实例并验证响应数据正确解析。

**验收场景**:

1. Given 接口类定义了 GET 请求，When 实例化并调用 `endpoint()`，Then Playwright 发送 HTTP GET 请求到正确的 URL（包含 query 参数、headers）。
2. Given 接口类定义了 POST 请求，When 实例化并传入 body，Then Playwright 发送 HTTP POST 请求，body 被正确序列化为 JSON。
3. Given 服务器返回 JSON 响应，When 调用接口，Then 响应自动解析为 Pydantic 响应模型实例，类型校验通过。
4. Given 服务器返回的 JSON 与响应模型不匹配（缺少字段或类型错误），When 调用接口，Then 抛出 Pydantic 校验异常并提供清晰的错误信息。

### 用户故事 3 - 从 OpenAPI 生成接口定义（优先级：P2）

测试工程师希望通过工具从 OpenAPI Specification 文件自动生成符合用户故事 1 中所定义的接口类结构。生成的接口类包含正确的 HTTP 方法声明、请求参数类型注解（Query/Body/Header/Path）、响应模型类型，以及对应的 Pydantic 请求/响应模型。

**为何优先**: 这是框架的生产力工具，将手动编写接口定义的工作自动化，降低接入成本。

**独立测试**: 准备一个包含多个端点的 OpenAPI YAML 文件，运行生成工具，验证生成的接口类符合用户故事 1 的格式、可正确导入、类型注解完整。

**验收场景**:

1. Given 用户提供 OpenAPI YAML 文件，When 运行生成工具，Then 生成的接口类结构符合用户故事 1 的伪代码格式（继承 APIRoute、使用 @router 装饰器、包含正确的参数定义）。
2. Given OpenAPI 定义了 GET /users 接口，When 查看生成的接口类，Then 包含 `@router.get(path="/users")` 装饰的接口类定义。
3. Given OpenAPI 定义了请求参数（query、path、header、body），When 查看生成的接口类，Then 参数类型注解、默认值、Query/Body/Header/Path 标记正确。
4. Given OpenAPI 定义了响应 schema，When 查看生成的代码，Then 包含对应的 Pydantic 响应模型类，字段类型与 OpenAPI 定义一致。


## 需求（必填）

### 功能性需求

- **FR-001**: 框架必须支持将 OpenAPI Specification 定义的 HTTP 接口直接转换为框架对接口的定义。
- **FR-002**: 框架必须提供声明式接口定义方式以描述请求与响应。
- **FR-003**: 框架必须基于 Pydantic 对请求构造与响应解析进行类型校验与序列化/反序列化。
- **FR-004**: 框架设计当前版本不强制依赖 FastAPI，采用"受其启发"的声明风格与注解设计，命名策略采用常见动词注解与参数标识：支持 `@get`, `@post`, `@put`, `@patch`, `@delete` 以及参数来源标记 `Query`, `Body`, `Header`, `Path`；这些参数标记类（Query/Body/Header/Path）的内部实现代码应参考 FastAPI 的实现方式，确保行为一致性和最佳实践；后续版本可根据需要选择性集成 FastAPI 的部分函数以增强功能。
- **FR-005**: 框架当前版本使用 Playwright 作为接口请求的客户端，采用同步实现方式（异步支持将在后续版本添加）；APIRouter 支持全局 servers 配置（类似 OpenAPI servers 机制），单个接口可在 RouteMeta 中指定优先级更高的 servers 配置，用于指定目标服务器的基础 URL；可根据实际情况调整为其他 HTTP 客户端库。
- **FR-006**: 框架应提供代码生成工具，从 OpenAPI 规范文件生成符合用户故事 1 定义格式的 Python 接口类代码、Pydantic 请求/响应模型，支持测试阶段直接加载生成代码；代码生成采用严格模式，遇到 OpenAPI 规范中包含框架尚未支持的特性时立即报错并停止生成，要求用户修改规范后重试，确保生成代码的完整性和可用性。
- **FR-007**: 生成的接口类、请求模型、响应模型应能正确导入使用；具体的目录结构组织方式（如 router.py、models.py 的划分）可在后续版本根据实际需求设计。
- **FR-008**: 提供代码生成的入口（具体命令名称、参数形式在后续实现时确定），至少支持指定输入的 OpenAPI 文件和输出目录。

### 非功能性需求

- **NFR-001 错误处理**: 框架必须在接口调用过程中对各类错误进行清晰分类并抛出详细的自定义异常类，包括但不限于：参数验证失败（ValidationError）、HTTP 请求失败（HTTPError）、响应解析失败（ParseError）；每个异常应包含足够的上下文信息便于调试和测试断言。
- **NFR-002 类型安全**: 框架必须充分利用 Python 类型系统，确保 IDE 和 mypy 等工具能提供完整的类型推断、自动补全和类型检查支持。
- **NFR-003 代码质量**: 生成的代码应遵循 Python 编码规范，具有良好的可读性和可维护性。

### 关键实体

- **接口定义（APIRoute）**: 名称、方法、路径、服务器列表（servers）、请求模型、响应模型。
- **请求模型（Request）**: 字段、必填/可选、默认值、校验规则、示例数据。
- **响应模型（Response）**: 字段、类型、可选/严格策略、容错策略。

## 成功标准（必填）

### 可度量结果

- **SC-001**: 新用户在 5 分钟内可完成从安装到将 OpenAPI Specification 定义转换为框架对接口的定义。

### 假设

- 默认目标为 HTTP 接口测试；非 HTTP 场景可通过用户自定义适配器扩展。
- 使用 Pydantic v2 语义进行类型定义与校验；若版本差异，需提供兼容指引。
- 报告由 pytest 生成；框架暂时不考虑生成测试报告，可选集成到外部平台不在本规范范围内。

### 技术约束

- **Python 版本**: 最低支持 Python 3.12，以使用 PEP 695 泛型新语法。
- **泛型语法**: 所有泛型类和函数必须使用 PEP 695 定义的新语法（`class ClassName[T]: ...` 和 `def function[T](...): ...`），禁止使用传统的 `Generic[T]` 继承方式。
- **参数标记类实现**: Query/Body/Header/Path 类的内部实现代码必须参考 FastAPI 的实现方式（`fastapi.params` 模块），包括但不限于：
  - 参数验证逻辑与错误处理机制
  - 与 Pydantic Field 的集成方式
  - 参数元数据的存储和传递方式
  - 别名、验证器的处理逻辑
  - **默认值处理**: 遵循 FastAPI 推荐的最佳实践，使用函数参数的默认值（`= value`）而非 `Query(default=value)` 等形式；Query/Body/Header/Path 不提供 `default` 参数，避免默认值声明的歧义和不一致。
- **同步实现优先**: 当前版本采用同步实现，异步支持在后续版本添加。

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

- Q: 响应模型的类型注解位置与可见性（基于类的接口设计中，如何在保持 __call__() 方法通用的前提下明确响应类型）? → A: 采用 Python 泛型（Generic）方案。生成的接口类继承 `APIRoute[T]`，通过泛型参数明确响应类型（如 `APIRoute[list[UserData]]`），既保证 IDE/mypy 可正确推断 `__call__()` 返回类型，又让响应模型在类定义处一目了然。子类无需定义 __call__() 方法，完全继承基类的通用实现。
- Q: 元数据在子类定义时需要 IDE 自动补全与类型提示，如何实现？ → A: 采用类型签名明确的类装饰器 `decorator(method, path)`（APIRouter 内部通过 `router.get/post/...` 调用），在类声明处传入元数据，IDE 可提供完整参数提示与校验；装饰器仅注入到类属性，内部更新逻辑封装在 `update_api_route`，保持代码简洁并符合“预生成静态代码”的设计。
- Q: 如何提供类似 FastAPI 的统一入口（如 router.get/router.post）？ → A: 提供 `APIRouter` 命名空间，内部方法（`get/post/put/patch/delete`）均调用同一个 `decorator` 入口以注入元数据；示例：`@router.get(path="/users")`，内层装饰器函数命名为 `update_api_route` 以贴近 FastAPI 源码风格。
### Session 2025-12-19

- Q: 接口类构造函数有重复代码（`self.limit = limit` 等），如何优化？并且避免框架属性名与用户字段冲突？ → A: 采用方案 2（元数据字典）。接口类继承 Pydantic BaseModel，自动生成 `__init__` 无需样板代码；所有路由元数据存储在单一的不可变 `RouteMeta` 对象，以 `_route_meta` ClassVar 存储，完全避免与用户字段冲突（用户可以安全地定义 method、path 等任意名称的字段）；提供 `route_meta()` 类方法供框架内部访问元数据。优势：零样板代码、最佳 IDE 支持、命名空间安全隔离、代码生成更清晰。

### Session 2025-12-24

- Q: APIRoute 基类的泛型语法选择? → A: 采用 Python 3.12 PEP 695 新语法 `class APIRoute[T]: ...` 替代传统 `class APIRoute(Generic[T]): ...`。项目 Python 最低版本已设定为 3.12，支持新语法；新语法更简洁清晰，无需从 typing 导入 Generic，改进了类型检查与 IDE 支持；代码生成产物中的接口类继承方式相应更新为 `class GetUsers(APIRoute[list[UserData]]): ...`，保持代码现代化与一致性。

### Session 2025-12-31

- Q: Query/Body/Header/Path 类本身的实现代码应该参考哪个框架或库的实现方式？ → A: 参考 FastAPI 的实现方式
- Q: 当接口调用过程中发生错误（如参数验证失败、HTTP 请求失败、响应解析失败）时，框架应该如何处理这些错误？ → A: 抛出详细的自定义异常类（ValidationError、HTTPError、ParseError 等）
- Q: `__call__()` 方法应该使用同步还是异步实现？ → A: 同步实现
- Q: Playwright 发送 HTTP 请求时需要知道目标服务器的基础 URL，框架应该如何获取这个配置？ → A: 在 APIRouter 中实现类似 OpenAPI servers 的机制来指定公共服务器，单个接口也可以在 RouteMeta 中指定自己的 servers（优先级更高）
- Q: 代码生成工具从 OpenAPI 规范生成接口类时，如果遇到 OpenAPI 规范中包含框架尚未支持的特性（如特殊的认证方式、自定义扩展字段等），应该如何处理？ → A: 严格模式 - 遇到不支持的特性立即报错并停止生成，要求用户修改规范