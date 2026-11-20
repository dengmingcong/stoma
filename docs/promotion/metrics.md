# 推广指标基线

本文件记录 Stoma 推广活动的指标基线与观测快照。

**采集脚本**：[`collect_metrics.sh`](./collect_metrics.sh)（无需认证的部分任何人都能跑；流量指标部分需 `gh` 认证）

---

## 基线快照（推广启动前）

**采集时间**：2026-11-16T08:05Z

| 指标 | 统计口径 | 基线值 | 采集命令 |
|------|----------|--------|----------|
| `repo_stars` | 仓库 Star 数（GitHub REST `stargazers_count`） | **0** | `curl -s https://api.github.com/repos/dengmingcong/stoma \| jq .stargazers_count` |
| `repo_watchers` | 仓库关注者数（GitHub REST **`subscribers_count`**） | **0** | `curl -s https://api.github.com/repos/dengmingcong/stoma \| jq .subscribers_count` |
| `repo_forks` | 仓库派生数（`forks_count`） | **0** | `curl -s https://api.github.com/repos/dengmingcong/stoma \| jq .forks_count` |
| `repo_open_issues` | 未关闭 Issue 数 | **0** | `curl -s https://api.github.com/repos/dengmingcong/stoma \| jq .open_issues_count` |
| `pypi_downloads_recent` | PyPI 近 30 日下载量（pypistats `last_month`） | **21** | `curl -s https://pypistats.org/api/packages/stoma/recent` |
| `pypi_downloads_week` | PyPI 近 7 日下载量（pypistats `last_week`） | **9** | 同上 |
| `pypi_downloads_total` | 自 2026-05-20 起累计下载量（含镜像源） | **1318** | `curl -s https://pypistats.org/api/packages/stoma/overall` |
| `pypi_downloads_total_no_mirror` | 同期累计下载量（不含镜像源） | **340** | 同上，按 `category=without_mirrors` 汇总 |
| `external_contributors` | 非作者贡献者数（排除 `dengmingcong` 与 `github-actions[bot]`） | **0** | `curl -s https://api.github.com/repos/dengmingcong/stoma/contributors` 后按 `login` 过滤 |
| `repo_traffic` | 仓库流量（访问量、来源域名、路径） | **暂不采集** | 需要 repo scope 的 token，且只覆盖滚动 14 天窗口 |

---

## 采集注意事项（三个已踩过的坑）

### 1. `watchers_count` 是 Star 的别名，不能用

GitHub REST API 的 `watchers_count` 字段**等于** `stargazers_count`，而真正的关注者数是 `subscribers_count`。实测对照（`sindresorhus/awesome`）：

```text
stargazers_count : 536501
watchers_count   : 536501   ← 是 star 的别名
subscribers_count: 8480      ← 真正的 watcher 数
```

用 `watchers_count` 记录「关注数」会**静默地**把关注数测错，且不会报错。当前仓库两个值都是 0，问题尚未显形 —— 所以基线脚本从一开始就写对了。

### 2. PyPI 项目页的下载量已被官方禁用

```
$ curl -s https://pypi.org/pypi/stoma/json | jq .info.downloads
{ "last_day": -1, "last_week": -1, "last_month": -1 }
```

这不是 bug —— Python Packaging User Guide 说明 PyPI 因 CDN 缓存导致数字「高度不准确」而主动移除。**必须用 pypistats.org**。

### 3. 贡献者列表含机器人

实测 `contributors` 端点返回 `['dengmingcong', 'github-actions[bot]']` —— **`github-actions[bot]` 也算贡献者**。统计「外部贡献者」（SC-007）时必须排除作者本人与以 `[bot]` 结尾的账号，否则基线就不是 0。

### 4. 下载量含 CI 通胀，不等于真人

GitHub Actions 矩阵中每次 `pip install stoma` 都产生一次下载。当前累计下载量中：

```text
with_mirrors    : 917   （含镜像源）
without_mirrors : 340   （不含镜像源）
不含镜像占比    : 37.1%
```

差异主要来自 CI 与镜像同步。求「真实用户」信号时应以 `without_mirrors` 为准，或用 BigQuery 的 `details.installer.name != 'pip'` 拆分。

> Packaging 官方指南原话：*"Just because a project has been downloaded a lot doesn't mean it's good."* —— 下载量是**触达**指标，不是**质量**指标。

---

## 目标值

| 指标 | 目标 | 依据 |
|------|------|------|
| `repo_stars` | ≥ 30（3 个月内） | 基线为 0；~~5+ 渠道下平均约 3 天 1 star~~ —— **本期只投 TesterHome 一个渠道，此目标值待重估** |
| `repo_watchers` | ≥ 10（3 个月内） | 关注数通常约为 star 的 1/3 |
| `pypi_downloads_total` | ≥ 300（3 个月内新增） | 对比基线速率 ~0.9 次/天 |
| `external_contributors` | ≥ 10 | SC-007；**本期不做贡献指引入口**，此目标值待重估 |
| `external_feedback` | ≥ 10 条（其中 ≥5 条来自实际使用者） | SC-006；**本期不设反馈渠道入口**，此目标值待重估 |

> **目标值的确定方式**：本节数值依据上表基线推导。**若调整目标值，须在本文件记录调整日期与理由**，以保证不同时间点的数值可比。

---

## 渠道投放后的观测安排

GitHub 流量 API 是**滚动 14 天窗口**，且只返回 Top 10 —— **不可事后回查**。因此每次投放后必须按以下节奏采集：

**本期只投 TesterHome 一个渠道**（2026-11-20 规格所有者决定），
投放后按以下节奏采集：

| 时点 | 动作 |
|------|------|
| 投放后 24 小时内 | 运行 `collect_metrics.sh`，把公开指标写入本文件下方快照 |
| +7 天 | 复采 |
| +14 天 | 复采 |
| +30 天 | 复采（观测社区互动，无阈值判定） |

> **渠道归因本期不做**（2026-11-20 规格所有者决定）—— 落地页与「从何处得知」自述均已取消，
> 流量指标也不采集。渠道来源由维护者在 `channels.md` 手动登记。
> 若后续需要来源域名级别的数据，再补采 `traffic/popular/referrers`（需 token、滚动 14 天窗口）。

> **重要**：GitHub 会对 **60 天无活动**的仓库禁用定时 workflow。若依赖 demo 仓的定时检测 job，须记住这一点（见 `research.md` R-4）。

---

## 观测快照

> 每次采集后在此追加一节。

### 2026-11-16 —— 基线

- **说明**：推广启动前的基线快照。流量指标因 `gh` 未认证暂缺。
- **数值**：见上方「基线快照」表。

<!-- 后续快照按时间倒序追加于此 -->

---

## 2026-11-20 推广范围收敛

一期只投 TesterHome 一个渠道，渠道归因机制取消。本文件的目标值（stars / watchers /
下载量 / 贡献者 / 反馈条数）原按「5 个渠道 + 反馈入口 + 贡献路径」推导，
在范围收敛后不再成立 —— 待 TesterHome 投放的实际反馈重新校准。

| 变更 | 原因 |
|------|------|
| 取消渠道归因（落地页 + 「从何处得知」自述） | GitHub 流量指标不采集，落地页是死链 |
| 不做 README 反馈章节 | 规格所有者决定（2026-11-20） |
| 只投 TesterHome | 规格所有者决定（2026-11-20） |
