# Tasks: Stoma 接口自动化测试框架

**Input**: Design documents from `.specify/specs/001-create-stoma/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: 本项目不包含自动化测试任务，按照规范说明"报告由 pytest 生成；框架暂时不考虑生成测试报告"。

**Organization**: 任务按用户故事分组，以便独立实现和测试每个故事。

## Format: `- [ ] [ID] [P?] [Story?] Description`

- **[P]**: 可并行执行（不同文件，无依赖）
- **[Story]**: 任务所属用户故事（如 US1, US2, US3）
- 描述中包含确切的文件路径

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths shown below follow plan.md structure

---

## Phase 1: Setup（项目初始化）

**Purpose**: 项目初始化和基础结构

- [X] T001 根据 plan.md 创建项目目录结构（src/, tests/unit, tests/integration, tests/contract）
- [X] T002 初始化 Python 3.12 项目并配置 pyproject.toml（添加 Pydantic v2, Playwright, Typer, PyYAML, jsonschema 依赖）
- [X] T003 [P] 配置代码格式化、类型检查和 linting 工具（ruff, mypy, flake8）
- [X] T004 [P] 配置 pre-commit hooks（集成 ruff, mypy, flake8, commitizen）
- [X] T005 [P] 安装 Playwright 并初始化浏览器（chromium）

---

## Phase 2: Foundational（核心基础设施）

**Purpose**: 所有用户故事依赖的核心基础设施，必须在任何用户故事之前完成

**⚠️ CRITICAL**: 此阶段完成前无法开始任何用户故事工作

**实现参考**: 所有实现必须严格遵循 [spec.md](spec.md) 中的伪代码示例，特别是：
- RouteMeta 必须继承 `pydantic.BaseModel` 并使用 `ConfigDict(frozen=True)` 实现不可变，包含 method、path、servers 字段
- APIRoute 必须继承 `BaseModel` 并使用 `ClassVar[RouteMeta]` 存储路由元数据，使用 PEP 695 泛型语法 `class APIRoute[T]: ...`
- 参数标记类型（Query/Path/Header/Body）的实现必须参考 FastAPI 的 `fastapi.params` 模块，包括参数验证逻辑、与 Pydantic Field 的集成方式、参数元数据的存储和传递方式、别名/验证器的处理逻辑
- **默认值处理**：遵循 FastAPI 最佳实践，使用函数参数默认值（`= value`）而非 `Query(default=value)`；Query/Body/Header/Path 不提供 `default` 参数

- [X] T006 创建 src/__init__.py 作为包入口
- [X] T007 [P] 实现 RouteMeta 类（继承 BaseModel，frozen=True，包含 method、path 和 servers 字段）in src/routing.py，参考 spec.md 用户故事 1 的伪代码
- [X] T008 [P] 实现参数标记类型（Query, Path, Header, Body）in src/params.py，必须参考 FastAPI 的 `fastapi.params` 模块实现，确保参数验证逻辑、Pydantic Field 集成、元数据存储/传递、别名/验证器处理与 FastAPI 行为一致；**不提供 `default` 参数**，遵循使用函数参数默认值的最佳实践

**Checkpoint**: 基础设施就绪 - 用户故事可以并行开始实现

---

## Phase 3: User Story 1 - 确定类型化接口定义格式（Priority: P0）🎯 MVP

**Goal**: 提供清晰、类型安全的接口定义格式，支持装饰器注入元数据、泛型响应类型、零样板代码、servers 配置机制

**Independent Test**: 手动编写示例接口类，验证类型注解、IDE 提示、装饰器语法的可用性

**实现参考**: 严格遵循 [spec.md](spec.md) 用户故事 1 的伪代码示例，特别关注：
- APIRoute[T] 基类设计：继承 BaseModel，使用 ClassVar[RouteMeta]，使用 PEP 695 泛型语法 `class APIRoute[T]: ...`
- api_route_decorator 装饰器签名和实现逻辑（支持 servers 参数），使用 PEP 695 泛型语法 `def api_route_decorator[T: APIRoute](...): ...`
- APIRouter 类的方法签名（get/post/put/patch/delete）使用 PEP 695 泛型语法，__init__ 支持全局 servers 配置
- 生成的接口类中，参数使用函数默认值形式（`= value`）而非 `Query(default=value)`

### Implementation for User Story 1

- [X] T009 [P] [US1] 实现 APIRoute[T] 基类（继承 Pydantic BaseModel，包含 _route_meta ClassVar）in src/routing.py
- [X] T010 [US1] 实现 api_route_decorator 装饰器函数（接收 method、path 和 servers 参数，返回类装饰器）in src/routing.py
- [X] T011 [US1] 实现 APIRouter 类（__init__ 接收全局 servers，提供 get/post/put/patch/delete 方法且支持接口级 servers 覆盖）in src/routing.py
- [X] T012 [US1] 验证装饰器语法与 IDE 类型提示（手动创建示例接口类测试）
- [X] T013 [US1] 验证命名空间隔离（测试用户字段名为 method、path 时无冲突）
- [X] T013a [US1] 验证 servers 配置机制（测试全局 servers 和接口级 servers 的优先级处理）

**Checkpoint**: User Story 1 完成，接口定义格式已确定并可手动编写接口类

---

## Phase 4: User Story 2 - 使用 Playwright 调用接口（Priority: P1）

**Goal**: 实现 APIRoute.send 方法，使用 Playwright 自动发送 HTTP 请求并解析响应（同步实现），支持 servers 配置和详织异常处理

**Independent Test**: 启动测试服务器，手动编写接口类并调用，验证请求发送和响应解析

**实现参考**: 参考 [spec.md](spec.md) 用户故事 2 的说明和示例，关注：
- APIRoute.send 方法的实现逻辑（参数收集、请求发送、响应解析）
- 直接使用传入的 APIRequestContext 发送 HTTP 请求（同步实现）
- 响应数据到 Pydantic 模型的转换流程
- servers 配置的解析与优先级处理（接口级 > 全局级）
- 错误处理：抛出 ValidationError、HTTPError、ParseError 等自定义异常

### Implementation for User Story 2

- [ ] T015 [US2] 实现请求参数收集逻辑（从 APIRoute 实例字段提取 query/path/header/body）in src/routing.py
- [ ] T015a [US2] 实现 servers 配置解析逻辑（从 RouteMeta 和 APIRouter 提取 servers，接口级优先级更高）in src/routing.py
- [ ] T016 [US2] 实现 URL 构造逻辑（基于 servers 配置 + 路径参数替换 + 查询参数拼接）in src/routing.py
- [ ] T017 [US2] 实现 HTTP 请求发送逻辑（GET/POST/PUT/PATCH/DELETE，使用传入的 APIRequestContext）in src/routing.py
- [ ] T017a [US2] 实现 HTTP 错误处理（连接失败、超时、HTTP 状态码错误时抛出 HTTPError）in src/routing.py
- [ ] T018 [US2] 实现响应 JSON 解析与 Pydantic 模型验证 in src/routing.py
- [ ] T018a [US2] 实现响应解析错误处理（JSON 解析失败抛出 ParseError，Pydantic 验证失败抛出 ValidationError）in src/routing.py
- [ ] T019 [US2] 实现 APIRoute.send 方法（集成上述所有逻辑，同步实现）in src/routing.py
- [ ] T020 [US2] 集成异常处理到 send 方法（确保所有错误都抛出清晰的自定义异常）in src/routing.py
- [ ] T021 [US2] 手动测试：启动 FastAPI 测试服务器，编写接口类并调用验证（包括 servers 配置和异常处理）

**Checkpoint**: User Story 2 完成，接口类可以真实调用 HTTP 服务并获得类型化响应

---

## Phase 5: User Story 3 - 从 OpenAPI 生成接口定义（Priority: P2）

**Goal**: 从 OpenAPI 文件自动生成符合 User Story 1 格式的接口类和 Pydantic 模型，支持严格模式和 servers 配置生成

**Independent Test**: 准备 OpenAPI YAML，运行生成工具，验证生成代码符合格式且可导入

**实现参考**: 参考 [spec.md](spec.md) 用户故事 3 的说明，关注：
- 生成的代码必须完全符合 User Story 1 定义的接口格式
- OpenAPI 各字段到 Python 类型的映射规则
- CLI 命令的参数设计（--spec, --out, --feature）
- 生成文件的目录结构和命名约定
- 严格模式：遇到不支持的 OpenAPI 特性立即报错并停止生成
- servers 配置生成：从 OpenAPI servers 字段提取并生成到 APIRouter 初始化和接口装饰器

### Implementation for User Story 3

- [ ] T022 [P] [US3] 实现 OpenAPI 文件读取与解析（支持 yaml/json）in src/codegen/parser.py
- [ ] T023 [P] [US3] 实现 OpenAPI schema 校验逻辑（使用 jsonschema）in src/codegen/parser.py
- [ ] T023a [US3] 实现严格模式检查（遇到不支持的 OpenAPI 特性立即抛出详细错误并停止生成）in src/codegen/parser.py
- [ ] T024 [US3] 实现 OpenAPI 组件提取（paths, methods, parameters, schemas, servers）in src/codegen/parser.py
- [ ] T025 [US3] 实现参数映射逻辑（OpenAPI parameter → Query/Path/Header/Body 标记）in src/codegen/parser.py
- [ ] T025a [US3] 实现 servers 配置解析逻辑（从 OpenAPI 全局 servers 和接口级 servers 提取）in src/codegen/parser.py
- [ ] T026 [P] [US3] 创建 Pydantic 模型生成模板 in src/codegen/templates/models.py.jinja2
- [ ] T027 [P] [US3] 创建接口类生成模板（包含装饰器、参数注解、servers 配置，参数默认值使用 `= value` 形式而非 `Query(default=value)`）in src/codegen/templates/routing.py.jinja2
- [ ] T028 [US3] 实现模板渲染器（Jinja2 渲染 routing 和 models）in src/codegen/renderer.py
- [ ] T029 [US3] 实现文件输出逻辑（按 feature 组织目录：routing.py, models.py）in src/codegen/renderer.py
- [ ] T030 [P] [US3] 实现 CLI 命令入口（stoma make --spec --out --feature）in src/cli.py
- [ ] T031 [US3] 添加 CLI 参数解析与校验（使用 Typer）in src/cli.py
- [ ] T032 [US3] 集成 parser, renderer, 文件输出到 CLI 工作流 in src/cli.py
- [ ] T033 [US3] 测试：准备示例 OpenAPI yaml（包含 servers 配置），运行 stoma make 验证生成代码
- [ ] T033a [US3] 测试：验证严格模式（使用包含不支持特性的 OpenAPI 文件，验证报错并停止）

**Checkpoint**: User Story 3 完成，可从 OpenAPI 自动生成完整的接口代码

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 跨用户故事的改进和完善

- [ ] T034 [P] 添加项目 README.md（安装、快速开始、使用示例）
- [ ] T035 [P] 添加代码文档字符串（遵循项目 docstring 规范）in src/routing.py, src/params.py
- [ ] T036 [P] 添加 CLI 帮助文档和使用示例 in src/cli.py
- [ ] T037 验证 quickstart.md 中的所有步骤可正常执行
- [ ] T038 代码清理：移除调试代码、优化导入、统一命名风格
- [ ] T039 [P] 性能验证：测试生成 ~200 endpoints 的 OpenAPI 是否在 5s 内完成

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 无依赖 - 可立即开始
- **Foundational (Phase 2)**: 依赖 Setup 完成 - 阻塞所有用户故事
- **User Stories (Phase 3-5)**: 全部依赖 Foundational 完成
  - User Story 1 (P0): 可在 Foundational 后立即开始 - 无其他用户故事依赖
  - User Story 2 (P1): 依赖 User Story 1 完成（需要 APIRoute 基类）
  - User Story 3 (P2): 依赖 User Story 1 完成（生成代码需要符合 US1 格式）
- **Polish (Phase 6)**: 依赖所有用户故事完成

### User Story Dependencies

- **User Story 1 (P0) - MVP**: Foundational 完成后可开始 - 最高优先级
- **User Story 2 (P1)**: 依赖 US1 的 APIRoute 基类和装饰器
- **User Story 3 (P2)**: 依赖 US1 的接口格式定义

### Within Each User Story

**User Story 1:**
- T007-T008 (Foundational) 必须先完成
- T009 (APIRoute 基类) 必须在 T010-T011 前完成
- T010-T011 可并行
- T012-T013 依赖所有实现任务

**User Story 2:**
- T009 (US1 的 APIRoute) 必须先完成
- T014-T018 可并行
- T019-T020 依赖 T014-T018
- T021 最后执行

**User Story 3:**
- T009 (US1 的 APIRoute) 必须先完成
- T022-T024 顺序执行（解析逻辑）
- T025-T027 可并行
- T028-T029 依赖 T025-T027
- T030-T032 顺序执行（CLI 逻辑）
- T033 最后执行

### Parallel Opportunities

**Setup Phase:**
- T003, T004, T005 可并行

**Foundational Phase:**
- T007, T008 可并行  

**User Story 1:**
- T012, T013 可并行（验证任务）

**User Story 2:**
- T014, T015, T016, T017, T018 可并行（不同功能模块）

**User Story 3:**
- T026, T027 可并行（不同模板）
- T030 可在 T022-T029 完成前开始（CLI 框架）

**Polish Phase:**
- T034, T035, T036 可并行
---

## Parallel Example: User Story 1

```bash
# 在 Foundational 完成后，可并行开始这些任务：
git checkout -b feature/us1-routing-base
# Developer A:
touch src/routing.py && code src/routing.py  # T009-T011

# Developer B (可以等 T009 完成后开始):
# T012 手动创建示例测试接口类
# T013 测试命名空间隔离
```

## Parallel Example: User Story 3

```bash
# Developer A:
touch src/codegen/parser.py && code src/codegen/parser.py  # T022-T025

# Developer B (并行):
mkdir -p src/codegen/templates
touch src/codegen/templates/models.py.jinja2  # T026
touch src/codegen/templates/routing.py.jinja2  # T027

# Developer C (可并行准备 CLI 框架):
touch src/cli.py && code src/cli.py  # T030
```

---

## Implementation Strategy

### MVP Scope (Minimum Viable Product)
- **Phase 1**: Setup
- **Phase 2**: Foundational  
- **Phase 3**: User Story 1 (P0) - 接口定义格式

**Rationale**: User Story 1 是框架的基础，完成后可以手动编写接口类进行初步验证。这是最小可用版本。

### Incremental Delivery
1. **Iteration 1 (MVP)**: Phase 1-3 → 可手动定义接口
2. **Iteration 2**: Phase 4 (US2) → 接口可真实调用 HTTP 服务
3. **Iteration 3**: Phase 5 (US3) → 可从 OpenAPI 自动生成代码
4. **Iteration 4**: Phase 6 (Polish) → 完善文档和优化

### Validation at Each Phase
- **After Setup**: 项目结构正确，依赖安装成功
- **After Foundational**: RouteMeta 和参数标记类可导入使用
- **After US1**: 手动编写的示例接口类类型检查通过，IDE 提示正确
- **After US2**: 示例接口类可成功调用测试服务器并获得响应
- **After US3**: 从示例 OpenAPI 生成的代码可导入并成功调用
- **After Polish**: quickstart.md 所有步骤可执行，文档完整

---

## Task Count Summary

- **Total Tasks**: 46 (原 39，新增 7 个任务）
- **Phase 1 (Setup)**: 5 tasks
- **Phase 2 (Foundational)**: 4 tasks (新增 T008a)
- **Phase 3 (User Story 1)**: 6 tasks (新增 T013a)
- **Phase 4 (User Story 2)**: 11 tasks (新增 T015a, T017a, T018a, T020)
- **Phase 5 (User Story 3)**: 14 tasks (新增 T023a, T025a, T033a)
- **Phase 6 (Polish)**: 6 tasks
- **Parallelizable Tasks**: 20 tasks marked with [P]

## Independent Test Criteria

### User Story 1 (接口定义格式)
- 可手动编写接口类，继承 APIRoute[T]
- 装饰器 @router.get/post 可正常使用，IDE 提供参数补全
- mypy 类型检查通过，返回类型推断正确
- 用户字段名与框架元数据无冲突

### User Story 2 (Playwright 调用)
- 启动测试服务器（如 FastAPI）
- 手动编写接口类并实例化
- 调用实例发送真实 HTTP 请求
- 响应正确解析为 Pydantic 模型
- 响应数据不匹配时抛出 Pydantic 校验异常

### User Story 3 (OpenAPI 生成)
- 准备包含多个端点的 OpenAPI YAML
- 运行 `stoma make --spec api.yaml --out ./gen --feature users`
- 生成的代码符合 User Story 1 格式
- 生成的接口类可导入并使用
- 类型注解完整，models.py 包含所有 schema

---

**Generated**: 2025-12-29 by /speckit.tasks command
**Feature Branch**: 001-create-stoma
**Source**: .specify/specs/001-create-stoma/
