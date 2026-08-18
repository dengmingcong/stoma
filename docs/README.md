# stoma 文档中心

## 这是什么

stoma 是从 OpenAPI 规范生成声明式接口测试代码的框架。给定一个 OpenAPI 文档，stoma 可以自动生成针对每条路由的测试脚手架，开发者只需填入业务断言即可完成接口验证。本文档集面向希望使用 stoma 编写接口测试的工程师，涵盖从入门到进阶的完整路径，以及 codegen 工具链和真实示例。

## 文档分区

本文档集分为三个部分。指南提供从入门到进阶的完整学习路径，覆盖日常测试编写的主要场景；codegen 深入介绍代码生成工具链的配置与内部规则；示例展示真实场景的完整测试实现。

### 指南

- [快速上手](./guide/quickstart.md) — 5 分钟跑通第一个 stoma 测试，了解核心概念与项目结构。文档涵盖环境搭建、CLI 安装与第一个测试的完整流程
- [定义路由](./guide/defining-routes.md) — 在测试中声明接口路由、HTTP 方法与路径参数的写法。包括路由前缀、路径参数解析与多方法路由的注册方式
- [客户端与认证](./guide/client-and-auth.md) — 配置测试客户端、注入 Token、处理鉴权头的常用模式。涵盖 Bearer Token、API Key 与自定义请求头的注入策略
- [参数与请求体](./guide/parameters.md) — 发送 Query、Header、Body 参数的声明式写法与最佳实践。支持必填校验、默认值与参数类型转换
- [响应与断言](./guide/response-and-validation.md) — 验证状态码、响应体结构与字段值的常用模式。内置 JSON Schema 断言与自定义业务规则断言写法
- [错误处理](./guide/error-handling.md) — 断言 4xx/5xx 错误响应的写法与自定义错误消息。介绍如何验证错误码、错误信息与异常场景覆盖

### codegen

- [stoma-make](./codegen/stoma-make.md) — 命令行工具完整参考：选项、生成规则、输出布局与多语言支持
- [生成规则](./codegen/generation-rules.md) — stoma 代码生成的内部规则与自定义配置选项详解

### 示例

- [端到端测试](./examples/end-to-end.md) — 从 OpenAPI 文档到完整测试套件的全流程示例，演示完整工作流。涵盖 spec 解析、路由匹配、测试用例生成与断言填写的完整链路

示例部分持续补充，欢迎在仓库中提 issue 反馈你希望看到的场景。

## 下一步

5 分钟上手：[`guide/quickstart.md`](./guide/quickstart.md)

如果已有 OpenAPI 文档，可直接运行 `stoma make --spec <path>` 生成测试代码。

## 反馈

文档与代码不一致时以代码为准。stoma 仍处于早期阶段，部分行为可能随版本迭代而变化，发现错误或遗漏请在仓库提 issue。
我们会尽快处理，也欢迎提交 PR 补充示例与修复文档。
