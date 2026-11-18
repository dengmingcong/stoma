# 推广渠道台账

本文件记录 Stoma 中文推广的投放渠道、投放状态与归因口径。

**语言**：本特性仅面向中文使用者（FR-007）。全部渠道的语言均为 `zh`。

---

## 字段说明

| 字段 | 含义 |
|------|------|
| **渠道标识** | 渠道的稳定短名，用于落地页文件名与 referrer 统计 |
| **平台** | 投放所在的网站 |
| **语言** | 恒为 `zh` |
| **内容定位** | 该渠道投放内容的切入角度与形态 |
| **与社区既有话题的关联说明** | 说明投放内容如何接上该社区本来就在讨论的话题（FR-011 要求） |
| **投放状态** | `未投放` / `已投放` / `已收录` |
| **投放时间** | 首次投放日期；未投放时留空 |
| **是否可被社区正常访问** | 投放后该链接是否无需登录即可访问 |
| **非作者互动数** | 30 天内来自非作者的实质性互动次数（SC-005 达标线为 ≥ 1） |
| **referrer 域名** | 从该渠道点进来时在流量统计中出现的来源域名 |
| **落地页路径** | 该渠道专属落地页在本仓的路径 |

---

## 社区渠道（计入 SC-005）

SC-005 要求：至少 5 个目标社区中发布 Stoma 介绍，且每个社区在发布后 30 天内产生至少一次非作者的实质性互动（提问、试用反馈或转发）。

| 渠道标识 | 平台 | 语言 | 内容定位 | 与社区既有话题的关联说明 | 投放状态 | 投放时间 | 可被社区正常访问 | 非作者互动数 | referrer 域名 | 落地页路径 |
|---|---|---|---|---|---|---|---|---|---|---|
| `juejin` | 掘金 | `zh` | 长文（800~3000 字，含可运行代码），以「在 IDE 和 Swagger 页面之间来回切」的个人工作流痛点切入 | 掘金的固定话题是「写点代码」—— 掘金读者按「有没有可运行的东西」筛选内容。本文的代码块与可克隆的 demo 仓库正是这一话题的答案。 | 未投放 |  |  | 0 | `juejin.cn` | [`docs/promotion/landings/juejin.md`](./landings/juejin.md) |
| `v2ex` | V2EX | `zh` | 主题帖，以「大家是怎么保证请求/响应模型和接口协议同步的？」提问式切入，帖内附答案与方案 | V2EX 的 `python` 与 `programmer` 节点长期有「请求/响应模型怎么和接口协议同步」的讨论。本帖以提问切入，接的是他们正在问的问题。 | 未投放 |  |  | 0 | `v2ex.com` | [`docs/promotion/landings/v2ex.md`](./landings/v2ex.md) |
| `zhihu` | 知乎 | `zh` | 回答「Python 接口自动化怎么做」类问题，以完整技术解答的形态展开 | 知乎「Python 接口自动化怎么做」类问题下聚集着选型中的开发者。本回答给的是完整的技术解答，接的是「怎么开始、用什么」的话题。 | 未投放 |  |  | 0 | `zhihu.com` | [`docs/promotion/landings/zhihu.md`](./landings/zhihu.md) |
| `oschina` | 开源中国 | `zh` | 软件投递，以软件能力介绍式组织内容 | 开源中国的读者在挑可用的开源软件。软件投递本身就是该站的既有话题形态 —— 项目 URL、中文描述、许可证、语言。 | 未投放 |  |  | 0 | `oschina.net` | [`docs/promotion/landings/oschina.md`](./landings/oschina.md) |
| `testerhome` | TesterHome（测试之家） | `zh` | 在 `接口测试` 节点以「请求/响应模型怎么和接口协议保持同步」式的痛点切入发帖，附方案与可运行代码 | `接口测试` 节点（node62，1519 个主题）聚集的正是维护接口测试套件的人。本帖接的是该节点反复出现的老问题：接口变了，模型怎么跟着改。 | 未投放 |  |  | 0 | `testerhome.com` | [`docs/promotion/landings/testerhome.md`](./landings/testerhome.md) |

---

## 被动发现面（不计入 SC-005）

以下两处是**已经存在**的入口，不需要投放动作。它们不产生社区互动，因此不计入 SC-005 的互动数统计。

| 渠道标识 | 平台 | 语言 | 内容定位 | 与社区既有话题的关联说明 | 投放状态 | 投放时间 | 可被社区正常访问 | 非作者互动数 | referrer 域名 | 落地页路径 |
|---|---|---|---|---|---|---|---|---|---|---|
| `pypi` | PyPI | `zh` | 项目页的 `long_description` 即主仓 README（由 US1 产出），是 Python 库最高意图的发现面 | PyPI 搜索「api testing」时项目页出现在结果里 —— 主动搜索是这类读者的既有行为。 | 已就位 | 2026-11-16 | 是 | 不适用 | `pypi.org` | [`README.md`](../../README.md) |
| `github-topics` | GitHub Topics | `zh` | 通过 `topic:api-testing` 等 topic 页被搜到，仓库的 topics 字段即入口 | `topic:api-testing` 等 topic 页是可浏览的列表页，GitHub 用户本就习惯从 topic 找工具。 | 已就位 | 2026-11-16 | 是 | 不适用 | `github.com` | [`README.md`](../../README.md) |

---

## 各渠道的投稿入口

以下入口在 2026-11-18 实测可达（`curl` 跟随重定向后的状态码）。

| 渠道 | 投稿入口 | 实测 |
|------|----------|------|
| `juejin` | <https://juejin.cn/post> | HTTP 200 |
| `v2ex` | <https://www.v2ex.com/new> | HTTP 200 |
| `zhihu` | <https://www.zhihu.com/question> | HTTP 403（反爬，浏览器可达） |
| `oschina` | <https://www.oschina.net/project/add> | HTTP 200 |
| `testerhome` | `接口测试` 节点 <https://testerhome.com/topics/node62> | HTTP 200 |
| `testerhome` | 开源项目收录 <https://testerhome.com/opensource_projects> | HTTP 200 |

> 💡 TesterHome 的节点 URL 形如 `/topics/node<N>`，`接口测试` 节点是 **node62**（实测「共有 1519 个讨论主题」）。
> 裸域名 `testerhome.com` 可达，**`www.testerhome.com` 连接失败** —— 分享链接一律用不带 `www` 的形式。

---

## 归因口径

**不采集需要 token 的 GitHub 流量指标**（T003 决定）。渠道归因靠两处配合完成：

1. **渠道专属落地页** —— 每个社区帖只指向自己那一份落地页（ART-06），绝不指向仓库根路径。这样 GitHub 流量统计里的 referrer 域名可区分 `juejin.cn` / `v2ex.com` / `zhihu.com` / `oschina.net` / `testerhome.com`。
2. **Discussions 的渠道自述** —— README 底部引导读者自述「第一次听说 Stoma 是从哪里？」，选项即上表中的渠道标识，由维护者汇总。

两条路径的结果都写回本文件的「非作者互动数」列。

---

## 更新记录

| 日期 | 变更 |
|------|------|
| 2026-11-18 | 建立台账。登记 5 个社区渠道与 2 个被动发现面，全部社区渠道处于「未投放」状态。 |
