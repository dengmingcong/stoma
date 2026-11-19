# OpenAPI 不该止步于接口文档：让 IDE 自动补全请求与响应

> 我是 Stoma 的作者。这篇文章讲两个具体问题，以及我们做的这个工具怎么回答它们。

---

## 一个具体场景

你接手一个接口自动化测试项目，需求文档里贴着一份 Swagger 链接。你打开 IDE，准备写第一个用例：

```python
requests.get("https://api.example.com/api/v3/user/user1")
```

然后你盯着 Swagger 页面找参数名：`username`？`userName`？必填还是选填？类型是 `string` 还是 `int`？

写完请求，你还要断言响应。于是再开一个标签页，对着 Swagger 的响应示例，比对 JSON 的层级：

```python
assert resp.json()["user"]["firstName"] == "John"
```

这套流程每个接口重复一遍。一个项目几百个接口，就是几百次「IDE ↔ 接口文档 ↔ 浏览器」的往返。

更麻烦的是第二件事：**你无法信任 IDE 的提示**。它对接口一无所知 —— 参数名写错不会有红线，字段名拼错要等到断言失败才知道。

## 规范里其实什么都有

OpenAPI 规范里，请求参数、每个状态码对应的响应结构，全都写得清清楚楚。问题在于规范是**给机器读的**（一份 JSON 或 YAML），不是给 Python 用的。

于是就出现了那套手工活：手写 Pydantic 模型、运行时再校验一遍响应结构、或者干脆从响应里现场推导字段。三种做法断在了同一个地方 —— **模型的来源是人，不是协议**。协议改了，模型不会跟着改。

这套流程还有一个隐蔽的代价：**协议新增字段时，你不会收到任何提示**。接口返回 200，用例照样绿，但断言还在对着旧结构做。多出来的数据被静默丢掉，测试看着通过，实际上什么都没验。

## Stoma：让规范直接生成代码

Stoma 的思路是把这一步反过来：**从 OpenAPI 生成 Pydantic 模型**。

FastAPI 是从 Pydantic 模型生成 OpenAPI 描述，Stoma 正好相反。

已经有规范的话，一行命令生成全部接口代码：

```bash
stoma spec.json --out app --prefix /api/v3
```

生成出来的接口定义，请求参数和响应结构都是**带类型的类属性**：

```python
@router.get("/user/{username}")
class GetUserByName(APIRoute):
    """按用户名查询用户。"""

    username: str
    """要查询的用户名，测试时用 user1"""

    @property
    def on_200_application_json(self) -> ResponseSpec[User]:
        return ResponseSpec(
            status_code=200,
            media_type="application/json",
            expected_type=User,
        )
```

## 请求参数：IDE 现在认识了

`username` 不再是字符串拼接里的一个字面量，而是一个**带类型的类属性**。写 `GetUserByName(` 的时候，IDE 直接告诉你这个接口要哪些参数、什么类型。

<img src="https://raw.githubusercontent.com/dengmingcong/stoma/master/docs/assets/readme/autocomplete.gif" alt="IDE 自动补全接口参数" />

生成的这份代码，和你手写的模型最大的区别不是长得像，而是**它有出处**。协议里的参数叫什么、是什么类型，生成结果里就是什么 —— 没有第二次转述的机会，也就没有抄错的可能。

## 响应类型：按状态码推导

OpenAPI 里一个接口可以声明多个状态码，每个状态码有自己的响应结构。Stoma 把它们拆成**每个状态码一个属性** —— `on_200_application_json` 对应成功时的 `User`，`on_400` 和 `on_404` 没有响应体，只需要校验状态码，`on_default` 兜住剩下的情况。

调用的时候，选你关心的那个协议：

```python
endpoint = GetUserByName(username="user1")
response = client.send(endpoint)

user = response.expect(endpoint.on_200_application_json)
```

`expect()` 按你选中的那个协议做三件事：校验状态码、校验媒体类型、按声明的类型校验响应体。字段对不上，抛的是 `ValidationError`，而不是一个等着人肉比对的 dict。

关键在**泛型**：`expect()` 的返回值类型由协议的类型参数推断出来。`on_200_application_json` 的类型是 `ResponseSpec[User]`，所以 `user` 就是 `User` —— IDE 知道，`user.first_name` 拼错了当场标红。

这也解决了状态码多起来之后的另一个麻烦。手工写的时候，「200 返回用户，404 返回空」这件事只存在于你的记忆里；生成之后，它变成了类里几个并排的属性 —— **看得见，就不容易记错**。

## 上下两层接起来了

请求侧，参数是类属性，IDE 能补全；响应侧，类型由「状态码 + 媒体类型」决定，IDE 同样知道。

两边合起来，就是同一件事：**代码即协议**。接口定义的来源不再是某个人的记忆，而是那份 OpenAPI 规范。规范改了，重新生成一次，代码跟着变。

## 上手

```bash
pip install stoma
```

需要 Python 3.12 及以上版本。依赖 Playwright 的 Python 包，但**不需要浏览器二进制** —— Stoma 只用 `APIRequestContext` 发请求，不启动浏览器。

想看完整示例，clone 一下 [stoma-demo](https://github.com/dengmingcong/stoma-demo) 仓库：

```bash
git clone https://github.com/dengmingcong/stoma-demo.git
cd stoma-demo
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
```

仓库里带的是 Swagger 官方 Petstore 的规范、生成好的接口定义，以及 8 个带断言的用例。

> ⚠️ 演示后端是 Swagger 官方 Petstore 公共服务，人人共享，可用性不保证，可能返回 HTTP 500 —— 这是服务状态问题，与 Stoma 无关。

## 我们想听到什么

Stoma 还在早期，API 和 CLI 都会调整。

比起 star，我们更想要的是你的反馈：生成的代码符合你的编码习惯吗？哪类接口形态还处理不了？文档里哪一段看不懂？

项目主页：https://github.com/dengmingcong/stoma

> 第一次听说 Stoma 是从哪里？欢迎在 Discussions 里说一声 —— 掘金、知乎、V2EX、开源中国、TesterHome、朋友推荐、搜索引擎，或者其他。
