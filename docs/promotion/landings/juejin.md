# Stoma —— 让 IDE 认识你的接口协议

> 掘金的朋友看这里：这篇文章配一个**可以直接克隆运行的仓库**，代码块都能跑。

Stoma 是一个 Python 接口自动化测试工具，核心是「**代码即协议**」。

写接口自动化时，IDE 不会联想接口参数 —— 你得左边开着 IDE，右边开着浏览器看接口文档；
调用完接口要对响应做断言，还得再对着协议比一遍结构。

Stoma 把接口协议直接变成代码：请求参数、响应结构、状态码，都是有类型的类属性。
IDE 直接联想，响应直接按声明的类型校验。

```python
@router.get("/user/{username}")
class GetUserByName(APIRoute):
    username: str

    @property
    def on_200_application_json(self) -> ResponseSpec[User]:
        return ResponseSpec(
            status_code=200,
            media_type="application/json",
            expected_type=User,
        )
```

`GetUserByName(username="user1")` 会自动补全；`response.expect(endpoint.on_200_application_json)`
会校验状态码、媒体类型，并把响应体转成 `User` 再断言。

## 有个仓库可以直接跑

[stoma-demo](https://github.com/dengmingcong/stoma-demo) 自带 Swagger 官方 Petstore 的 OpenAPI 规范、
Stoma 生成的接口定义，和 8 个带断言的测试用例。克隆下来就能跑通完整链路：

```bash
git clone https://github.com/dengmingcong/stoma-demo.git
cd stoma-demo
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
```

想看「从协议到代码」的全过程：

```bash
stoma spec.json --out app --prefix /api/v3
```

## 需要知道的几件事

- **这是 Alpha**（v0.3.0），API 与 CLI 仍可能调整。需要 **Python ≥ 3.12**。
- 依赖 Playwright 的 Python 包，但**不需要浏览器二进制** —— 它只用 `APIRequestContext` 发请求，
  不启动浏览器，不用执行 `playwright install`。依赖 PyPI 上已发布的 `stoma>=0.3.0,<0.4.0`。
- 演示后端是 Swagger 官方 Petstore **公共服务**，人人共享，可用性不保证，可能返回 HTTP 500 ——
  这是服务状态问题，与 Stoma 无关。

## 文档与反馈

- [快速开始](https://github.com/dengmingcong/stoma/blob/master/docs/guide/quickstart.md)
- [关于 Stoma](https://github.com/dengmingcong/stoma/blob/master/docs/about.md) —— 项目由来与灵感
- 问题与建议：[Stoma Discussions](https://github.com/dengmingcong/stoma/discussions)

> 第一次听说 Stoma 是从哪里？欢迎在 Discussions 里说一声 —— 掘金、知乎、V2EX、开源中国、
> TesterHome、朋友推荐、搜索引擎，或者其他。
