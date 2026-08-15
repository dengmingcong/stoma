# 接口认证方案指南

> 调研用途：梳理常见 HTTP 接口认证方式的差异、明确 `Bearer` 与 `JWT` 的关系，
> 作为 stoma 后续实现 `Auth` 抽象的概念基础。

---

## 一、常见认证方式概览

按「凭证存放位置 + 传输方式」两个维度梳理，覆盖业界主流方案。

### 1. HTTP Basic Auth

```http
Authorization: Basic base64(username:password)
```

- **凭证**：用户名 + 密码。
- **特点**：每次请求都带原始凭证（base64 可逆，几乎等于明文）。
- **场景**：内部工具、API 调试、简单脚本。
- **缺点**：HTTPS 才有意义；不适合现代应用主流程。
- **典型工具**：curl `-u user:pass`、Postman "Basic Auth"。

### 2. Bearer Token（最主流）

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xxx.yyy
```

- **凭证**：服务端签发的不透明字符串 / JWT。
- **获取方式**：先调登录接口（`/auth/login`）拿 token，再带 token 访问业务接口。
- **场景**：OAuth2 / OpenID Connect、绝大多数现代 REST API、GitHub / Google / Stripe。
- **变体**：
  - **JWT**：自包含 claims（用户 ID、过期时间），无需服务端会话存储。
  - **Opaque Token**：随机字符串，服务端查表校验（更安全，可主动吊销）。
- **缺点**：需要管理 token 生命周期（过期、刷新）。

### 3. Cookie + Session（最古老、最常见于浏览器）

```http
Cookie: sessionid=abc123; csrftoken=xyz789
```

- **凭证**：服务端生成的 session ID，存在服务端存储（Redis / DB）。
- **配套**：浏览器自动管理；客户端要手动存 `Cookie` 头。
- **场景**：传统 Web 应用、FastAPI SessionMiddleware、Django、Express Session。
- **配套机制**：
  - **CSRF Token**：防止跨站请求伪造（攻击者拿不到 cookie）。
  - **SameSite / Secure / HttpOnly**：浏览器侧安全策略。
- **缺点**：有状态、需要服务器存 session、跨域麻烦。

### 4. API Key

```http
X-API-Key: sk-xxx
```

> 也常放在 query：`?api_key=sk-xxx`（不推荐）。

- **凭证**：服务方预先生成的静态字符串。
- **场景**：服务端到服务端（如 OpenAI / Stripe API key）、Webhook 验证、CI 调用。
- **缺点**：粒度粗（一般是「全权限」），泄露后必须重发。

### 5. OAuth 2.0 流程（Bearer 的「上游」）

OAuth2 是**颁发 token 的协议族**，不是认证本身：

| 模式 | 适用 | 说明 |
|------|------|------|
| Authorization Code | 第三方登录 | 浏览器跳转、回调 code、换 token |
| Client Credentials | 服务端调用服务端 | 机器对机器，无用户参与 |
| Password Grant | 自家应用 | 用户名密码直换 token（已不推荐） |
| Refresh Token | 长会话 | 用 refresh_token 换新 access_token |

stoma 这种**测试框架主要跟 Client Credentials 和 Password Grant 打交道**（脚本场景），Authorization Code 需要浏览器跳转，超出框架职责。

### 6. mTLS / 证书认证

```text
不是 HTTP header，而是 TLS 握手层：
客户端证书 → 服务端校验
```

- **凭证**：客户端证书 + 私钥。
- **场景**：银行 / 政府 API、零信任网络、Kubernetes API Server。
- **缺点**：运维复杂，不适合普通业务。

### 7. HMAC 签名（AWS SigV4 / 阿里云风格）

```http
Authorization: AWS4-HMAC-SHA256 Credential=AKIA..., Signature=xxx
```

- **凭证**：AccessKey + SecretKey（用 SecretKey 对请求做 HMAC 签名）。
- **场景**：云厂商 API（AWS / 阿里云 / 腾讯云）、金融行业。
- **特点**：请求体、时间戳都参与签名，防篡改。
- **缺点**：实现复杂、调试困难。

### 8. WebAuthn / Passkey（前沿）

- **凭证**：设备生物识别 + 私钥签名。
- **场景**：现代浏览器登录、密码替代。
- **不适用**：自动化测试框架（需要真人交互）。

### 在 stoma 场景下的优先级

| 优先级 | 方式 | 理由 |
|--------|------|------|
| ⭐⭐⭐ | Bearer Token | OAuth2 / 现代 API 几乎都是这个 |
| ⭐⭐⭐ | Cookie Session | FastAPI / 传统 Web 后端测试刚需 |
| ⭐⭐ | API Key | 一行 header，配置简单 |
| ⭐ | HMAC | 云厂商 API 调测需要，工作量大 |
| ❌ | Basic Auth | 已经被 Bearer 取代，无需单独支持（用户塞 header 即可） |
| ❌ | mTLS / OAuth Code | 框架层不该管，交给 Playwright / 浏览器 |

---

## 二、Bearer 是什么

**Bearer = 持有者**。在 HTTP `Authorization` 头里，Bearer 是一个**认证方案名**（scheme），告诉服务器：「任何持有这个 token 的人都是合法用户」。

### 现实类比

去游乐园买票，门票上印着 `Bearer Ticket`（不记名票）。检票员只看**谁拿着这张票**，不查身份证。这正是 Bearer 的语义：**凭票认证，不验证持票人身份**。

HTTP 头长这样：

```http
Authorization: Bearer abc123xyz
```

| 部分 | 含义 |
|------|------|
| `Authorization` | 头名 |
| `Bearer` | **认证方案名**（scheme） |
| `abc123xyz` | **凭证内容**（可以是任何东西：随机字符串、JWT、UUID） |

### 为什么用 Bearer

HTTP 标准（RFC 6750）需要给认证方式起个名字，服务器才能区分：

```http
Authorization: Basic dXNlcjpwYXNz        # Basic 方案
Authorization: Bearer abc123             # Bearer 方案
Authorization: Digest ...                # Digest 方案
Authorization: AWS4-HMAC-SHA256 ...      # AWS 签名方案
```

### Bearer 这个词能改吗

能。如果你的 API 不走 RFC，自己定义也行：

```http
X-Auth-Token: abc123                     # 完全不用 Authorization 头
Authorization: Token abc123              # 方案名写 Token（GitHub 早期用过）
Authorization: MyScheme xxx              # 自定义方案名
```

但业界 99% 用 Bearer，因为它语义清晰、跨语言 SDK 默认支持。

---

## 三、JWT 是什么

**JWT = JSON Web Token**，一种**token 的数据格式**。它解决了「token 里要塞什么信息」的问题。

### 一个真实 JWT 长这样

```text
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
  .eyJ1c2VyX2lkIjoxMjM0LCJleHAiOjE3MDAwMDAwMDB9
  .signature_here
```

三段用 `.` 分隔，解码后是：

```json
Header:    { "alg": "HS256", "typ": "JWT" }
Payload:   { "user_id": 1234, "exp": 1700000000 }
Signature: HMAC-SHA256(header + "." + payload, secret_key)
```

### JWT 解决了什么问题

没有 JWT 时，服务端只能这样查 token：

```python
# 服务端：拿 token 去数据库 / Redis 查
def verify(token: str):
    user = db.query("SELECT * FROM sessions WHERE token = ?", token)
    return user  # 每次都要查库
```

有了 JWT，**信息塞进 token 里**，服务端不用查库：

```python
# 服务端：验签 + 解码 payload，不用查库
def verify(token: str):
    payload = jwt.decode(token, secret_key, algorithms=["HS256"])
    return payload["user_id"]  # 拿到用户信息了
```

### JWT 的三大特点

1. **自包含**：用户信息、过期时间、权限都写在 payload 中。
2. **签名防伪**：服务端用密钥签发，客户端改不了内容。
3. **无状态**：服务端不用存 session，验证只看签名是否正确。

---

## 四、Bearer 和 JWT 的关系

**Bearer 是协议层（怎么传），JWT 是数据层（token 里装什么）**。它们是正交的两件事。

| 维度 | Bearer | JWT |
|------|--------|-----|
| 是什么 | HTTP 认证方案名 | token 的数据格式 |
| 负责 | 告诉服务器「凭证在 Authorization 头」 | 决定凭证里**装什么信息** |
| 标准 | RFC 6750 | RFC 7519 |
| 类比 | 信封的**投递方式**（挂号信） | 信封里的**内容**（信件格式） |

### 组合示例

最常见的现代 API：

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxMjM0fQ.xxx
               └────────┘  └──────────────────────────────────────────┬──────────────────────────────────────────┘
              方案名                              JWT 格式的 token（Header.Payload.Signature）
```

也可以这样组合（不常见但合法）：

```http
Authorization: Bearer 550e8400-e29b-41d4-a716-446655440000
               └────────┘  └────────────────────┬─────────────────────┘
                  方案名            随机字符串（Opaque Token）
```

或者更冷的搭配：

```http
X-Auth: JWT eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
# 自定义头 + 自定义方案名 + JWT 格式（不规范，但有人这么用）
```

---

## 五、用 Python 实际看一下

### 不透明 Token（Opaque）

```python
# 登录成功后，服务端返回一个随机字符串
{"access_token": "550e8400-e29b-41d4-a716-446655440000", "token_type": "Bearer"}

# 服务端存：{ "550e8400...": {"user_id": 1234, "exp": 1700000000} }
# 每次请求都要查这个映射表
```

### JWT Token

```python
import jwt

# 签发
token = jwt.encode(
    {"user_id": 1234, "exp": 1700000000},
    key="my-secret",
    algorithm="HS256",
)
# token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxMjM0LCJleHAiOjE3MDAwMDAwMDB9.xxx"

# 验证（不用查库）
payload = jwt.decode(token, key="my-secret", algorithms=["HS256"])
# payload = {"user_id": 1234, "exp": 1700000000}
```

---

## 六、关键差异对比

| 维度 | 不透明 Token (Opaque) | JWT |
|------|----------------------|-----|
| 服务端能否立刻看到用户 ID | ❌ 需要查库 / 查缓存 | ✅ payload 里直接有 |
| 服务端能否主动吊销 | ✅ 从 DB 删除记录 | ⚠️ 只能等过期（或用黑名单） |
| 性能 | 每次请求都查存储 | 纯 CPU 验签 |
| 大小 | 小（UUID 几十字节） | 较大（几百字节到几 KB） |
| 泄露后危害 | 可立即吊销 | 在过期前一直有效 |
| 典型使用 | 传统 OAuth 服务、微信 | 内部系统、移动端 API |

---

## 七、一句话总结

> **Bearer 是「信封的投递方式」，JWT 是「信封的格式」。**
> 绝大多数现代 API 用的是 **「Bearer 投递 + JWT 格式」** 的组合，
> 但你也可以用「Bearer 投递 + 随机字符串」——后端会自动选。

---

## 八、延伸阅读方向

- **stoma 该怎么抽象这层**：让用户写 `class Login(...)` 就自动完成所有事。
- **JWT 的安全陷阱**：哪些字段不该放 payload、密钥怎么管。
- **token 刷新机制**：access_token 短 + refresh_token 长，怎么写状态机。