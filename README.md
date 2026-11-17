# Stoma

Stoma 是一个接口自动化和接口自动化测试工具，尝试实现「代码即协议」来解决如下问题：

* 代码中请求 HTTP 接口，IDE 不能自动联想接口参数，需要左边屏幕打开 IDE，右边屏幕在浏览器打开接口协议。
* 从响应中提取信息或者对响应断言时，同样需要左右对比查看结构。

现在 IDE 可以自动联想 Stoma 接口和响应。

<img width="80%" style="border-radius: 8px;" alt="Image" src="https://raw.githubusercontent.com/dengmingcong/stoma/master/docs/assets/readme/autocomplete.gif" />

Stoma 提供了 CLI 自动生成接口。

<img width="80%" style="border-radius: 8px;" alt="Image" src="https://raw.githubusercontent.com/dengmingcong/stoma/master/docs/assets/readme/cli.gif" />

## 安装

需要 Python 3.12 或更高版本。

```bash
pip install stoma
```

Stoma 依赖 Playwright 的 Python 包，但**不需要浏览器二进制** —— 它只用 Playwright 的
`APIRequestContext` 发送请求，不启动浏览器，因此无需执行 `playwright install` 下载浏览器组件。

## 最小示例

定义接口、调用接口、对响应断言，三步完成。

```python
from pydantic import BaseModel, Field
from stoma import APIRoute, APIRouter, ResponseSpec


class User(BaseModel):
    id: int | None = None
    username: str
    first_name: str | None = Field(default=None, alias="firstName")


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

调用并断言：

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
    assert user.first_name
```

接口定义与断言响应是同一套模型 —— `GetUserByName` 用 `username: str` 声明请求参数，
用 `on_200` 声明响应协议，`response.expect()` 会校验 Status Code 与 Media type，
并把响应体转成 `User`。响应里的 `firstName` 会按模型声明的别名映射到 `first_name`。

> 上面查询的是 Swagger 官方 Petstore 公开演示服务。它是**人人共享的公共服务，
> 可用性不保证，可能返回 HTTP 500** —— 这是服务状态问题，与 Stoma 无关。

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
uv run pytest -v
```

没有 uv 也可以走 pip：

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

- [关于 Stoma](https://github.com/dengmingcong/stoma/blob/master/docs/about.md) — 项目由来、灵感与依赖。
- 许可证：[MIT](https://github.com/dengmingcong/stoma/blob/master/LICENSE)
