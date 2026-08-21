# Stoma

Stoma 是一个接口自动化和接口自动化测试工具，尝试实现「代码即协议」来解决如下问题：

* 代码中请求 HTTP 接口，IDE 不能自动联想接口参数，需要左边屏幕打开 IDE，右边屏幕在浏览器打开接口协议。
* 从响应中提取信息或者对响应断言时，同样需要左右对比查看结构。

## 指南

- [快速开始](./docs/guide/quickstart.md) — 安装并以真实接口为例介绍用法。
- [定义路由](./docs/guide/defining-routes.md) — 在测试中声明接口路由、HTTP 方法与路径参数的写法。包括路由前缀、路径参数解析与多方法路由的注册方式
- [客户端与认证](./docs/guide/client-and-auth.md) — 配置测试客户端、注入 Token、处理鉴权头的常用模式。涵盖 Bearer Token、API Key 与自定义请求头的注入策略
- [参数与请求体](./docs/guide/parameters.md) — 发送 Query、Header、Body 参数的声明式写法与最佳实践。支持必填校验、默认值与参数类型转换
- [响应与断言](./docs/guide/response-and-validation.md) — 验证状态码、响应体结构与字段值的常用模式。内置 JSON Schema 断言与自定义业务规则断言写法
- [错误处理](./docs/guide/error-handling.md) — 断言 4xx/5xx 错误响应的写法与自定义错误消息。介绍如何验证错误码、错误信息与异常场景覆盖

## 脚手架工具

- [脚手架工具](./docs/codegen/stoma-make.md) — 命令行工具完整参考：选项、生成规则、输出布局与多语言支持
- [生成规则](./docs/codegen/generation-rules.md) — stoma 代码生成的内部规则与自定义配置选项详解

## 实例

- [Petstore 示例](./docs/examples/petstore.md) — Swagger 官方 Petstore (OpenAPI 3.0.4) 的 stoma 演示

