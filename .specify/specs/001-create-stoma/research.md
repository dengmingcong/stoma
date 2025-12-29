# Research

## Decision: 目录分层参考 FastAPI 源码（routing/params/client/codegen/cli/templates）
- Rationale: 与用户要求对齐，保持熟悉的命名和分层（类似 fastapi/routing、params、applications），便于将装饰器、路由元数据与参数标记解耦，生成模板也可紧贴同构目录。APIRoute 基类合并到 routing.py 以保持核心路由逻辑集中。
- Alternatives considered: 扁平化 `stoma/`（降低目录层级但混合职责，后续扩展困难）；按领域拆包（如 http/generator/runner），但与 FastAPI 源码风格不一致，学习成本更高；独立 models.py（额外分层但核心路由类与装饰器过于分散）。

## Decision: 默认 HTTP 客户端采用 Playwright，同步保留可替换接口
- Rationale: 规格已指明 Playwright；其上下文和浏览器会话可支持更复杂场景（如需要 cookie、鉴权、前置流程），并提供稳定的 async API，减少自封装成本。
- Alternatives considered: httpx/requests（更轻但与“浏览器级”验证不符）；aiohttp（轻量但额外配置 SSL/Session）；保留抽象以便未来替换。

## Decision: CLI 采用 Typer，输入格式固定为 `stoma make --spec <openapi> --out <dir> --feature <name>`
- Rationale: Typer 基于 Click，提供类型注解与自动帮助文档，契合“易用性优先”与类型安全要求；参数形态已在澄清会话确定。
- Alternatives considered: argparse（标准库但缺少自动补全与类型提示）；纯脚本入口（最少依赖但可维护性差，扩展子命令困难）。

## Decision: OpenAPI 解析流程 = 读取 (yaml/json) → 校验 → 生成模板上下文
- Rationale: 通过 PyYAML + jsonschema 校验可早期发现规范错误；提取路径/方法/参数/组件后映射到模板，便于在生成阶段保持类型完整性。
- Alternatives considered: 直接依赖 third-party 生成器（如 openapi-python-client），但无法按 Stoma 的 APIRoute 风格输出；完全手写解析（代码量大，复用度低）。
