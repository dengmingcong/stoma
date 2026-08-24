# Stoma

Stoma 是一个接口自动化和接口自动化测试工具，尝试实现「代码即协议」来解决如下问题：

* 代码中请求 HTTP 接口，IDE 不能自动联想接口参数，需要左边屏幕打开 IDE，右边屏幕在浏览器打开接口协议。
* 从响应中提取信息或者对响应断言时，同样需要左右对比查看结构。

## 指南

- [快速开始](./docs/guide/quickstart.md) — 安装并以真实接口为例介绍用法。
- 定义接口 — Stoma 中一个接口由接口路由、接口参数和响应协议组成。
    * [接口路由](./docs/guide/define-routes.md)
    * [接口参数](./docs/guide/define-parameters.md)
    * [响应协议](./docs/guide/define-response-specs.md)
- [接口请求和断言](./docs/guide/client.md) — 使用 `Client` 调用接口，对接口响应断言。
- [生成接口](./docs/guide/cli.md) — Stoma 提供了 CLI 命令基于 OpenAPI 协议自动生成接口。

## 实例

- [Petstore](./tests/examples/petstore/) — 演示如何使用 Stoma 定义并调用 Swagger 官方 [Petstore](https://petstore3.swagger.io/) 接口。

## 关于

[关于 Stoma](./docs/about.md) - 关于项目的说明。
