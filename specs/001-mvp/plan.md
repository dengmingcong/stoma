# 实施计划：Stoma 001-mvp

**分支**: `001-mvp` | **日期**: 2025-12-15 | **规范**: specs/001-mvp/spec.md
**输入**: 功能规范来自 `/specs/001-mvp/spec.md`

**说明**: 此模板由 `/speckit.plan` 命令填充。请参阅 `.specify/templates/commands/plan.md` 了解执行工作流。

## 摘要

从 OpenAPI 生成声明式 API 测试套件的框架。技术方案：通过 CLI (`stoma make`) 预生成 Python 代码到按功能组织的包中（`router.py`, `models.py`），使用 Pydantic v2 进行校验，通过 Playwright 执行 HTTP 请求，并输出可读的 HTML + 控制台报告。

## 技术上下文

<!--
  需要操作：将本节内容替换为项目的技术细节。
  此处结构仅作为建议，用于指导迭代过程。
-->

**语言/版本**: Python 3.11  
**主要依赖**: Playwright, Pydantic v2  
**存储**: 无  
**测试框架**: pytest  
**目标平台**: macOS/Linux CI  
**项目类型**: 单一 CLI + 库  
**性能目标**: 待明确（例如：100 接口代码生成 < 2s；请求运行 p95 < 300ms）
**约束条件**: 待明确（例如：HTML 报告大小 < 5MB；并发限制）
**规模/范围**: 待明确

## 宪章检查

*门槛：必须在 Phase 0 研究前通过。Phase 1 设计后重新检查。*

门槛：
- 库优先：交付库 + CLI 入口点。
- CLI 接口：`stoma make` 必须支持 JSON/人类可读输出。
- 测试优先：在实现前定义契约/集成测试（待明确具体测试清单）。
- 可观测性/版本控制/简洁性：优先使用文本 I/O，结构化日志，语义化版本（待明确细节）。

## 项目结构

### 文档（本功能）

```text
specs/[###-feature]/
├── plan.md              # 本文件（/speckit.plan 命令输出）
├── research.md          # Phase 0 输出（/speckit.plan 命令）
├── data-model.md        # Phase 1 输出（/speckit.plan 命令）
├── quickstart.md        # Phase 1 输出（/speckit.plan 命令）
├── contracts/           # Phase 1 输出（/speckit.plan 命令）
└── tasks.md             # Phase 2 输出（/speckit.tasks 命令 - 不由 /speckit.plan 创建）
```

### 源代码（仓库根目录）
<!--
  需要操作：将下面的占位符树替换为此功能的具体布局。
  删除未使用的选项，并用真实路径扩展所选结构（例如 apps/admin, packages/something）。
  最终计划不应包含选项标签。
-->

```text
src/
└── example/
  └── <feature>/
    ├── __init__.py
    ├── router.py
    └── models.py

tests/
├── contract/
├── integration/
└── unit/
```

**结构决策**: 在 `src/example/<feature>` 下按功能组织包，包含 `router.py` 和 `models.py`。

## 复杂度跟踪

> **仅在宪章检查存在必须证明的违规时填写**

| 违规项 | 为何需要 | 拒绝更简单替代方案的原因 |
|--------|---------|-------------------------|
| [例如：第 4 个项目] | [当前需求] | [为何 3 个项目不足] |
| [例如：仓储模式] | [具体问题] | [为何直接 DB 访问不足] |
