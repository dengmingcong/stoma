# Stoma

<p align="center">
  <a href="https://pypi.org/project/stoma/"><img alt="PyPI version" src="https://img.shields.io/pypi/v/stoma.svg"></a>
  <a href="https://pypi.org/project/stoma/"><img alt="Python versions" src="https://img.shields.io/pypi/pyversions/stoma.svg"></a>
  <a href="https://img.shields.io/pypi/dm/stoma.svg"><img alt="PyPI downloads" src="https://img.shields.io/pypi/dm/stoma.svg"></a>
  <a href="https://github.com/dengmingcong/stoma/blob/master/LICENSE"><img alt="License" src="https://img.shields.io/github/license/dengmingcong/stoma.svg"></a>
</p>

<p align="center"><b>Typed HTTP API Definitions for Python.</b></p>

<p align="center">Your IDE autocompletes them.</p>

<p align="center">
  <img width="80%" style="border-radius: 8px;" alt="IDE 自动联想接口参数" src="https://raw.githubusercontent.com/dengmingcong/stoma/master/docs/assets/readme/autocomplete.gif" />
</p>

<!-- README-I18N:START -->

<p align="center">
  <a href="https://github.com/dengmingcong/stoma/blob/master/README.md">English</a> ·
  <b>中文</b>
</p>

<!-- README-I18N:END -->

<p align="center">
  <a href="#安装">安装</a> ·
  <a href="#示例">示例</a> ·
  <a href="#关键特性">关键特性</a> ·
  <a href="#文档">文档</a> ·
  <a href="#关于">关于</a>
</p>

---

## 安装

需要 Python 3.12 或更高版本。

```bash
pip install stoma
```

## 示例

声明接口：

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

调用接口：

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

## 关键特性

- **代码即协议** —— Stoma 保存接口调用所需的所有信息，调用接口时再也不用在 IDE 和接口文档之间切换。
- **IDE 自动补全** —— 得益于 Pydantic 和泛型，IDE 可以自动补全请求参数和响应类型。
- **接口测试** —— 定义接口、调用接口、对带类型的响应断言。
- **每个状态码都有独立的响应类型** —— 每个 HTTP 状态码都有自己的响应类型，且可静态推导。
- **AI 能读懂它** —— 方法、路径、参数名与类型、每个状态码的响应类型、docstring：全部写在定义里，AI 拿到手就有所需信息。
- **代码生成** —— 一条 CLI 命令即可基于 OpenAPI 规范生成整套接口代码。
  <img width="80%" style="border-radius: 8px;" alt="stoma CLI 生成接口代码" src="https://raw.githubusercontent.com/dengmingcong/stoma/master/docs/assets/readme/cli.gif" />

Stoma 用来**定义并调用** HTTP API —— 它不实现服务端路由。
手动定义与从规范生成是**两条并列的路**：OpenAPI 是一种**输入来源**，不是使用的前提。CLI 这条路适用于可获得 OpenAPI 规范（或可转换为 OpenAPI 规范）的开放接口；没有规范时，自己手写定义同样可行。接口变更时重新生成即可，定义与规范不会脱节。


## 文档

- [快速开始](https://github.com/dengmingcong/stoma/blob/master/docs/guide/quickstart.zh.md) — 安装并以真实接口为例介绍用法。
- 定义接口 — Stoma 中一个接口由接口路由、接口参数和响应协议组成。
    * [接口路由](https://github.com/dengmingcong/stoma/blob/master/docs/guide/define-routes.zh.md)
    * [接口参数](https://github.com/dengmingcong/stoma/blob/master/docs/guide/define-parameters.zh.md)
    * [响应协议](https://github.com/dengmingcong/stoma/blob/master/docs/guide/define-response-specs.zh.md)
- [接口请求和断言](https://github.com/dengmingcong/stoma/blob/master/docs/guide/client.zh.md) — 使用 `Client` 调用接口，对接口响应断言。
- [生成接口](https://github.com/dengmingcong/stoma/blob/master/docs/guide/cli.zh.md) — Stoma 提供了 CLI 命令基于 OpenAPI 协议自动生成接口。

也可以看看演示仓库 [stoma-demo](https://github.com/dengmingcong/stoma-demo)，演示在实际项目中如何使用 Stoma。


## 关于

[关于 Stoma](https://github.com/dengmingcong/stoma/blob/master/docs/about.zh.md) — 项目由来、灵感与依赖。
