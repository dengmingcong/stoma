# 任务清单：Stoma 001-generate-api

**分支**: `001-generate-api` | **日期**: 2025-12-15 | **规范**: [spec.md](spec.md) | **计划**: [plan.md](plan.md)

## 概述

本文档将功能实现分解为可独立执行的任务，按用户故事组织以支持增量交付与并行开发。

**关键原则**:
- 每个用户故事是独立可测试的增量
- 标记 `[P]` 的任务可并行执行（不同文件、无依赖）
- MVP 范围：仅用户故事 1
- 建议按阶段顺序执行

## 实施策略

### MVP 优先（推荐首次交付）
- **范围**: Phase 1 Setup + Phase 2 Foundational + Phase 3 用户故事 1
- **价值**: 端到端验证核心工作流（OpenAPI → 代码生成 → 模型定义）
- **时间**: 约 80% 的任务在 MVP 中

### 增量交付
1. Phase 1-2: 搭建基础设施
2. Phase 3: 实现核心代码生成能力（MVP）
3. Phase 4: 补充测试运行与报告功能

---

## Phase 1: Setup（项目初始化）

**目标**: 建立项目结构、依赖管理与开发环境。

### 任务列表

- [ ] T001 创建项目根目录结构：`src/`, `tests/`, `specs/`
- [ ] T002 初始化 `pyproject.toml`，声明项目元信息与依赖（Pydantic v2, Playwright, pytest）
- [ ] T003 [P] 创建 `src/__init__.py` 作为包入口
- [ ] T004 [P] 创建 `.gitignore`，排除 `__pycache__/`, `.pytest_cache/`, `*.egg-info/`
- [ ] T005 [P] 创建 `README.md`，包含快速开始与安装说明
- [ ] T006 配置开发环境：验证 Python 3.11，安装依赖

---

## Phase 2: Foundational（基础能力 - 阻塞所有用户故事）

**目标**: 实现所有用户故事依赖的共享基础设施。

### 任务列表

- [ ] T007 创建 CLI 入口点：`src/cli/__init__.py` 和 `src/cli/main.py`
- [ ] T008 实现 `stoma` CLI 主命令框架（使用 argparse 或 click）
- [ ] T009 [P] 创建 OpenAPI 解析器模块：`src/parser/openapi_parser.py`
- [ ] T010 实现 OpenAPI 到内部模型的转换逻辑（读取 paths, schemas, operations）
- [ ] T011 [P] 创建代码生成器基类：`src/codegen/base_generator.py`
- [ ] T012 [P] 创建模板引擎或字符串构建工具用于代码生成

**完成标准**: 
- CLI 可成功注册并响应 `stoma --help`
- OpenAPI 解析器可读取示例 YAML 并提取端点信息

---

## Phase 3: 用户故事 1 - 从 OpenAPI 生成代码（优先级：P1）

**目标**: 用户可通过 CLI 从 OpenAPI 规范生成 Python 代码（router.py, models.py），结构化输出按 feature 组织。

**为何优先**: 核心价值主张，决定框架易用性与采用成本。

**独立测试标准**: 
- 准备一个最小 OpenAPI YAML（含 1 个端点 GET /users）
- 执行 `stoma make --spec openapi.yaml --out src/example --feature users`
- 验证生成 `src/example/users/router.py` 和 `src/example/users/models.py`
- 检查模型包含正确的 Pydantic 字段定义

### 任务列表

#### 模型生成

- [ ] T013 [P] [US1] 创建 Pydantic 模型生成器：`src/codegen/model_generator.py`
- [ ] T014 [US1] 实现从 OpenAPI schemas 生成 Request 类（字段、类型、必填/可选、默认值）
- [ ] T015 [US1] 实现从 OpenAPI schemas 生成 Response 类（字段、类型、验证规则）
- [ ] T016 [US1] 添加字段注解支持（Query, Body, Header, Path 标记）

#### 路由生成

- [ ] T017 [P] [US1] 创建路由生成器：`src/codegen/router_generator.py`
- [ ] T018 [US1] 实现 Endpoint 类定义生成（名称、方法、路径、关联模型）
- [ ] T019 [US1] 为每个 HTTP 方法生成装饰器注解（@get, @post, @put, @patch, @delete）
- [ ] T020 [US1] 生成路由函数签名与模型绑定

#### CLI 集成

- [ ] T021 [US1] 实现 `stoma make` 子命令在 `src/cli/make.py`
- [ ] T022 [US1] 添加参数解析：`--spec`, `--out`, `--feature`
- [ ] T023 [US1] 集成 OpenAPI 解析器与代码生成器流程
- [ ] T024 [US1] 实现按 feature 创建目录结构（`<out>/<feature>/`）
- [ ] T025 [US1] 生成 `__init__.py`, `router.py`, `models.py` 文件到目标目录

#### 输出格式

- [ ] T026 [P] [US1] 实现代码格式化（使用 black 或内置格式器）
- [ ] T027 [P] [US1] 添加生成代码的文件头注释（自动生成警告、版本信息）

#### 测试与验证

- [ ] T028 [US1] 创建集成测试：`tests/integration/test_generate_command.py`
- [ ] T029 [US1] 测试完整生成流程（OpenAPI → 生成代码 → 验证文件存在）
- [ ] T030 [US1] 测试生成的 Pydantic 模型可正常导入与实例化
- [ ] T031 [US1] 测试边界情况：空 OpenAPI、无效路径、重复 feature 名

**Phase 3 完成标准**:
- ✅ CLI 命令 `stoma make` 可成功执行
- ✅ 生成目录结构符合 `<out>/<feature>/router.py`, `<out>/<feature>/models.py`
- ✅ 生成的代码可通过 Python 语法检查（`python -m py_compile`）
- ✅ 生成的 Pydantic 模型包含正确的字段、类型与验证器
- ✅ 集成测试通过，验证端到端生成流程

---

## Phase 4: Polish & 跨功能改进

**目标**: 补充测试运行能力、报告生成、错误处理与文档。

### 任务列表

#### Playwright 集成（测试运行）

- [ ] T032 [P] 创建 Playwright 客户端封装：`src/runner/http_client.py`
- [ ] T033 实现基于生成路由的测试用例自动生成逻辑
- [ ] T034 实现 `stoma run` 命令执行测试套件
- [ ] T035 [P] 添加请求超时、重试配置

#### 报告生成

- [ ] T036 [P] 创建报告生成器：`src/reporter/html_reporter.py`
- [ ] T037 实现控制台摘要输出（通过/失败统计）
- [ ] T038 实现 HTML 报告生成（套件统计、用例明细、失败差异对比）
- [ ] T039 [P] 添加输入摘要与定位信息到报告

#### 错误处理与可观测性

- [ ] T040 [P] 实现结构化日志：`src/utils/logger.py`
- [ ] T041 [P] 添加详细错误消息与堆栈跟踪
- [ ] T042 实现 CLI 输出 JSON 格式支持（`--json` 标志）
- [ ] T043 [P] 添加进度指示器（生成/运行阶段）

#### 文档与示例

- [ ] T044 [P] 创建完整示例 OpenAPI 规范：`examples/petstore.yaml`
- [ ] T045 [P] 编写用户指南：`docs/user-guide.md`（安装、生成、运行、报告）
- [ ] T046 [P] 编写 API 参考文档
- [ ] T047 [P] 更新 README 包含完整示例与截图

#### 测试覆盖

- [ ] T048 [P] 补充单元测试覆盖 OpenAPI 解析器
- [ ] T049 [P] 补充单元测试覆盖模型生成器
- [ ] T050 [P] 补充单元测试覆盖路由生成器
- [ ] T051 补充端到端测试（生成 → 运行 → 报告）

---

## 依赖关系图

### 关键路径（必须顺序执行）

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational: CLI框架 + OpenAPI解析器)
    ↓
Phase 3 (User Story 1: 代码生成核心)
    ↓
Phase 4 (Polish: 测试运行 + 报告)
```

### 用户故事完成顺序

1. **User Story 1** (P1): 必须首先完成，是框架核心
2. 未来扩展空间：
   - User Story 2: 高级验证策略（自定义校验器）
   - User Story 3: 批量测试场景生成
   - User Story 4: CI/CD 集成

---

## 并行执行机会

### Phase 1 可并行
- T003, T004, T005 (文件创建互不依赖)

### Phase 2 可并行
- T009 (解析器) || T011, T012 (生成器基础)

### Phase 3 可并行
- T013-T016 (模型生成) || T017-T020 (路由生成)
- T026, T027 (格式化与文件头) 可在生成器完成后并行

### Phase 4 可并行
- T032 (Playwright) || T036 (报告) || T040-T043 (日志/错误)
- T044-T047 (文档) 可随时并行
- T048-T050 (单元测试) 可在对应模块完成后并行

---

## 验证清单

### MVP 验证（Phase 1-3 完成后）

- [ ] 用户可在 5 分钟内完成：安装 → 准备 OpenAPI → 运行 `stoma make` → 检查生成代码
- [ ] 生成的代码结构符合 fastapi-best-practices 风格
- [ ] 生成的模型可导入且类型安全（通过 mypy 检查）
- [ ] CLI 提供清晰的帮助信息与错误提示

### 完整验证（Phase 4 完成后）

- [ ] 端到端流程：生成 → 运行测试 → 查看 HTML 报告
- [ ] 报告包含所有必需元素（统计、差异、输入摘要）
- [ ] 错误场景有友好提示（无效 OpenAPI、网络失败等）
- [ ] 文档完整且示例可运行

---

**任务统计**:
- 总任务数: 51
- Phase 1 Setup: 6 任务
- Phase 2 Foundational: 6 任务
- Phase 3 User Story 1 (MVP核心): 19 任务
- Phase 4 Polish: 20 任务
- 可并行任务: 约 22 任务（标记 `[P]`）

**建议 MVP 范围**: T001-T031（前 31 任务），可独立交付核心代码生成能力。
