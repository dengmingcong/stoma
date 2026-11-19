# Stoma

<p align="center">
  <a href="https://pypi.org/project/stoma/"><img alt="PyPI version" src="https://img.shields.io/pypi/v/stoma.svg"></a>
  <a href="https://pypi.org/project/stoma/"><img alt="Python versions" src="https://img.shields.io/pypi/pyversions/stoma.svg"></a>
  <a href="https://img.shields.io/pypi/dm/stoma.svg"><img alt="PyPI downloads" src="https://img.shields.io/pypi/dm/stoma.svg"></a>
  <a href="https://github.com/dengmingcong/stoma/blob/master/LICENSE"><img alt="License" src="https://img.shields.io/github/license/dengmingcong/stoma.svg"></a>
</p>

<p align="center"><b>用 OpenAPI 定义接口，用 Python 调用接口 —— 代码即协议。</b></p>

<p align="center">
  <a href="#安装">安装</a> ·
  <a href="#30-秒-demo">30 秒 Demo</a> ·
  <a href="#为什么-stoma">为什么 Stoma</a> ·
  <a href="#完整示例">完整示例</a> ·
  <a href="#指南">指南</a> ·
  <a href="#示例项目">示例项目</a> ·
  <a href="#关于">关于</a>
</p>

---

## 安装

需要 Python 3.12 或更高版本。

```bash
pip install stoma
```

Stoma 依赖 Playwright 的 Python 包，但**不需要浏览器二进制** —— 它只用 Playwright 的
`APIRequestContext` 发送请求，不启动浏览器，因此无需执行 `playwright install` 下载浏览器组件。

依赖的 Stoma 版本范围为 `stoma>=0.3.0,<0.4.0`。

> **Stoma 当前是 Alpha 阶段（v0.3.0）**，API 与 CLI 仍可能调整。
> 本文档目前只有中文版，英文版随后提供。

## 30 秒 Demo

调用一个接口，就是一次普通的 Python 调用：

```python
endpoint = GetUserByName(username="user1")
response = client.send(endpoint)
user = response.expect(endpoint.on_200)
assert user.username == "user1"
```

参数名、参数类型、响应结构，全部由 IDE 校验 —— 接口规范就是代码本身，
不再需要在 IDE 和接口文档之间来回切换。

Stoma 也提供 CLI，能直接从 OpenAPI 规范生成全部接口代码：

<img width="80%" style="border-radius: 8px;" alt="stoma CLI 生成接口代码" src="https://raw.githubusercontent.com/dengmingcong/stoma/master/docs/assets/readme/cli.gif" />

## 为什么 Stoma

写接口自动化测试时，下面三件事最消耗时间。

### 1. 写请求参数时，IDE 什么都不知道

用裸字符串调接口时，URL 和参数都是没有约束的文本：

```python
client.get("https://api.example.com/user", params={"user_nmae": "user1"})  # 拼错了，运行时才发现
```

Stoma 里接口是一个 Pydantic 模型，参数名写错、类型写错，IDE 当场标红：

```python
endpoint = GetUserByName(username="user1")
```

### 2. 断言响应时，要肉眼比对 JSON 结构

手写 `response.json()["user"]["firstName"]` 这种写法，字段拼错了要等断言失败才知道，
失败信息还只是一个 `KeyError`。

Stoma 会按响应协议校验并解析响应，返回的就是模型对象：

```python
user = response.expect(endpoint.on_200)
assert user.first_name == "John"  # IDE 能补全，字段名写错立刻报错
```

### 3. 几百个接口，一个一个手工抄

Stoma 提供 CLI，直接从 OpenAPI 规范生成全部接口代码：

```bash
stoma spec.json --out app --prefix /api/v3
```

## 完整示例

以 Swagger Petstore 的 [getUserByName](https://petstore3.swagger.io/#/user/getUserByName) 接口为例。

### 1. 定义接口

接口由「路由 + 参数 + 响应协议」组成，写法和定义 Pydantic 模型一样：

```python
from typing import Annotated

from pydantic import BaseModel, Field

from stoma import APIRoute, APIRouter, ResponseSpec


class User(BaseModel):
    id: Annotated[int | None, Field(examples=[10])] = None
    """Example: 10"""

    username: Annotated[str | None, Field(examples=["theUser"])] = None
    """Example: 'theUser'"""

    first_name: Annotated[str | None, Field(alias="firstName", examples=["John"])] = None
    """Example: 'John'"""


router = APIRouter(prefix="/api/v3")


@router.get("/user/{username}")
class GetUserByName(APIRoute):
    """按用户名查询用户。"""

    username: str

    @property
    def on_200(self) -> ResponseSpec[User]:
        return ResponseSpec(
            status_code=200,
            media_type="application/json",
            expected_type=User,
        )
```

### 2. 调用接口

Stoma 基于 Playwright 的 [APIRequestContext](https://playwright.dev/python/docs/api/class-apirequestcontext)
发送请求，Cookie、代理、超时、并发等 Playwright 特性全部可用。

```python
from playwright.sync_api import sync_playwright

from stoma import Client

with sync_playwright() as p:
    ctx = p.request.new_context(base_url="https://petstore3.swagger.io")
    client = Client(context=ctx)

    endpoint = GetUserByName(username="user1")
    response = client.send(endpoint)
    user = response.expect(endpoint.on_200)
    assert user.username == "user1"
```

### 3. IDE 里自动联想

Stoma 把所有接口定义为 Pydantic 模型，所以 IDE 能自动联想所有参数：

<img width="80%" style="border-radius: 8px;" alt="IDE 自动联想接口参数" src="https://raw.githubusercontent.com/dengmingcong/stoma/master/docs/assets/readme/autocomplete.gif" />

鼠标悬浮即可查看参数说明：

<img width="80%" style="border-radius: 8px;" alt="悬浮查看参数说明" src="https://raw.githubusercontent.com/dengmingcong/stoma/master/docs/assets/guide/quickstart/hover-param.png" />

响应同样是强类型对象，`expect()` 的返回值类型由泛型推断：

<img width="80%" style="border-radius: 8px;" alt="IDE 自动联想响应类型" src="https://raw.githubusercontent.com/dengmingcong/stoma/master/docs/assets/guide/quickstart/ide-autocomplete-response.png" />

## 从 OpenAPI 生成接口

`stoma` 命令读取 OpenAPI 规范（3.0 / 3.1，支持 YAML 和 JSON），生成可运行的接口代码：

```bash
stoma spec.json --out app --prefix /api/v3
```

生成结果：

```text
app/
├── models.py       # 数据模型
├── router.py       # 路由汇总
└── endpoints/      # 每个接口一个文件
```

生成过程支持按状态码和媒体类型生成响应协议、表单与文件上传请求体、以及字段名自动转为
snake_case；遇到规范中暂不支持的形态会跳过该接口并给出提示，而不是中断整批生成。

## 指南

- [快速开始](https://github.com/dengmingcong/stoma/blob/master/docs/guide/quickstart.md) — 安装并以真实接口为例介绍用法。
- 定义接口 — Stoma 中一个接口由接口路由、接口参数和响应协议组成。
    * [接口路由](https://github.com/dengmingcong/stoma/blob/master/docs/guide/define-routes.md)
    * [接口参数](https://github.com/dengmingcong/stoma/blob/master/docs/guide/define-parameters.md)
    * [响应协议](https://github.com/dengmingcong/stoma/blob/master/docs/guide/define-response-specs.md)
- [接口请求和断言](https://github.com/dengmingcong/stoma/blob/master/docs/guide/client.md) — 使用 `Client` 调用接口，对接口响应断言。
- [生成接口](https://github.com/dengmingcong/stoma/blob/master/docs/guide/cli.md) — Stoma 提供了 CLI 命令基于 OpenAPI 协议自动生成接口。

## 示例项目

[stoma-demo](https://github.com/dengmingcong/stoma-demo) 是一个可独立克隆运行的完整项目
—— 它自带 Petstore 的 OpenAPI 规范、生成的接口定义和带断言的测试，
克隆下来就能跑通「定义接口 → 调用 → 断言」的完整链路，无需任何额外配置。

```bash
git clone https://github.com/dengmingcong/stoma-demo.git
cd stoma-demo
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
```

演示后端是 Swagger 官方 [Petstore](https://petstore3.swagger.io/) 公共服务，
因此运行测试需要联网。它是**人人共享的公共服务，可用性不保证，可能返回 HTTP 500**
—— 这是服务状态问题，与 Stoma 无关。

## 关于

### 项目状态

Stoma 目前处于 **Alpha** 阶段（v0.3.0），接口仍可能调整。

### 参与

Stoma 还在早期，最有价值的贡献是**使用反馈**：哪些接口场景覆盖不到、生成代码是否符合你的
编码习惯、文档哪里看不懂，都可以来讨论。

- 问题与建议：[Stoma Discussions](https://github.com/dengmingcong/stoma/discussions)
- 如果愿意一起完善，欢迎提交 PR。

本地开发：

```bash
git clone https://github.com/dengmingcong/stoma.git
cd stoma
uv sync
uv run pytest
```

### 许可证

[MIT](https://github.com/dengmingcong/stoma/blob/master/LICENSE)

- [关于 Stoma](https://github.com/dengmingcong/stoma/blob/master/docs/about.md) — 项目由来、灵感与依赖。
