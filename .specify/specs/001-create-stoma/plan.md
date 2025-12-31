# Implementation Plan: Stoma 接口自动化测试框架

**Branch**: `001-create-stoma` | **Date**: 2025-12-26 | **Spec**: [specs/001-create-stoma/spec.md](specs/001-create-stoma/spec.md)
**Input**: Feature specification from `/specs/001-create-stoma/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

构建一个仿 FastAPI 声明式风格的接口自动化测试框架 Stoma，核心做法是：接口类继承 Pydantic BaseModel 并通过泛型 `APIRoute[T]` 声明响应类型，使用类装饰器（`router.get/post/...`）注入路由元数据 `_route_meta`，运行时由基类 `__call__` 用 Playwright 发送 HTTP 请求并将 JSON 反序列化为类型安全的响应模型；提供 CLI `stoma make --spec --out --feature` 从 OpenAPI 预生成接口类、请求/响应模型，输出目录结构参考 FastAPI 源码分层。

## Technical Context

**Language/Version**: Python 3.12（使用 PEP 695 泛型新语法）  
**Package Manager**: uv（包管理与依赖锁定）  
**Primary Dependencies**: Pydantic v2（类型校验/序列化）、Playwright（HTTP 客户端，同步实现）、typer/argparse（CLI 外壳，最终选型在实现阶段可微调）、PyYAML + jsonschema（OpenAPI 解析/校验）  
**Storage**: N/A（仅代码生成与 HTTP 调用，无持久化）  
**Testing**: pytest（含示例/集成用例，验证生成代码与 Playwright 调用）  
**Target Platform**: 本地与 CI（macOS/Linux），纯 Python 环境  
**Project Type**: CLI + 库（代码生成工具与运行时 SDK）  
**Performance Goals**: 生成阶段 < 5s 处理中等规模 OpenAPI（~200 endpoints）；运行阶段单次调用开销接近 Playwright 原生，主要关注类型安全而非极致性能  
**Constraints**: 
- 不引入 FastAPI 运行时依赖，但 Query/Body/Header/Path 类的内部实现必须参考 FastAPI 的 `fastapi.params` 模块（包括参数验证逻辑、与 Pydantic Field 的集成方式、参数元数据的存储和传递方式、默认值/别名/验证器的处理逻辑）
- 生成产物必须零样板、可直接导入；保持 Pydantic v2 语义
- HTTP 客户端可替换但默认 Playwright，当前版本采用同步实现（异步支持在后续版本添加）
- 错误处理机制：必须抛出详细的自定义异常类（ValidationError、HTTPError、ParseError 等），包含足够的上下文信息
- 代码生成采用严格模式：遇到 OpenAPI 规范中包含框架尚未支持的特性时立即报错并停止生成
- servers 配置：APIRouter 支持全局 servers（类似 OpenAPI servers 机制），单个接口可在 RouteMeta 中指定优先级更高的 servers
**Scale/Scope**: 面向中小型 API 套件（10-300 endpoints），支持多 feature 包并行维护

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- 易用性优先：接口类零样板，装饰器注入元数据，生成产物可直接导入 — 符合宪法原则一。
- 类型安全与 IDE 支持：使用 Pydantic v2 + Python 3.12 的 PEP 695 泛型语法，生成代码全量类型注解 — 符合原则四。
- 独立性与兼容性：不强制依赖 FastAPI，命名沿用通用 get/post/Query/Body 等约定 — 符合原则三。
- 代码生成质量：预生成 OpenAPI → Python，产物遵循项目编码规范与 docstring 规范 — 符合原则五。

## Project Structure

### Documentation (this feature)

```text
specs/001-create-stoma/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md (由 /speckit.tasks 生成)
```

### Source Code (repository root)

```text
.
├── src/
│   ├── __init__.py
│   ├── routing.py          # 仿 FastAPI 的装饰器、路由元数据与 APIRoute 基类（APIRouter、decorators、RouteMeta、APIRoute，支持全局 servers 配置）
│   ├── params.py           # Query/Path/Header/Body 标记与校验辅助（参考 fastapi.params 实现，包括参数验证逻辑、与 Pydantic Field 的集成、元数据存储传递、默认值/别名/验证器处理）
│   ├── exceptions.py       # 自定义异常类（ValidationError、HTTPError、ParseError 等，包含详细上下文信息）
│   ├── client.py           # Playwright HTTP 包装与请求构造（同步实现，支持 servers 配置解析与优先级处理）
│   ├── cli.py              # stoma make 命令入口与参数解析（Typer）
│   └── codegen/            # OpenAPI 解析、模板渲染、文件生成（严格模式：遇到不支持特性立即报错）
│       ├── __init__.py
│       ├── parser.py
│       ├── renderer.py
│       └── templates/
└── tests/
    ├── unit/               # 单元测试：路由元数据、参数标记、模板渲染、异常类
    ├── integration/        # 集成测试：生成产物可导入、基础调用链、servers 配置、错误处理
    └── contract/           # OpenAPI 输入与生成结果比对、严格模式验证
```

**Structure Decision**: 源码直接置于 `src` 根部，遵循 FastAPI 源码的模块化文件布局（routing.py/params.py 等为单文件），仅在代码生成需要时使用 `codegen/` 子目录，避免新增 `src/stoma` 之类的多层包结构；APIRoute 基类合并到 routing.py 以保持核心路由逻辑集中；测试继续按单元/集成/契约划分。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
