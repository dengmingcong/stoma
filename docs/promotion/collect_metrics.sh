#!/usr/bin/env bash
# docs/promotion/collect_metrics.sh —— 推广指标采集
#
# 采集无需认证的公开指标（任何人都能跑）：
#   - PyPI 下载量（pypistats）
#   - GitHub 仓库公开字段
#
# 用法：
#   docs/promotion/collect_metrics.sh [包名] [仓库路径]
#   docs/promotion/collect_metrics.sh stoma dengmingcong/stoma
#
# 输出的原始数值用于更新 docs/promotion/metrics.md 的基线快照。
#
# 注：GitHub 的流量指标（traffic/*，含 referrers 与 paths）需要 repo scope 的
# token，且只覆盖滚动 14 天窗口 —— 当前阶段不采集，需要时再行补充。

set -euo pipefail

PKG="${1:-stoma}"
REPO="${2:-dengmingcong/stoma}"

echo "=== 采集时间 ==="
date -u '+%Y-%m-%dT%H:%M:%SZ'

echo
echo "=== PyPI 下载量（pypistats，无需认证） ==="
curl -fsS "https://pypistats.org/api/packages/${PKG}/recent"
echo

curl -fsS "https://pypistats.org/api/packages/${PKG}/overall" | python3 -c '
import json, sys
data = json.load(sys.stdin)["data"]
totals = {}
for row in data:
    totals[row["category"]] = totals.get(row["category"], 0) + row["downloads"]
for category in sorted(totals):
    print(f"  {category}: {totals[category]}")
print(f"  days_covered: {len(data)}")
'

echo
echo "=== GitHub 仓库公开字段（无需认证） ==="
curl -fsS "https://api.github.com/repos/${REPO}" | python3 -c '
import json, sys
d = json.load(sys.stdin)
print("  stars        :", d["stargazers_count"])
# 注意：watchers_count 在 REST API 中是 stargazers_count 的别名，不是真正的关注者数。
# 真正的 watcher 数是 subscribers_count —— 用 watchers_count 会静默地测错 SC-004。
print("  watchers     :", d["subscribers_count"], " # subscribers_count, 非 watchers_count")
print("  forks        :", d["forks_count"])
print("  open_issues  :", d["open_issues_count"])
print("  topics       :", d.get("topics"))
print("  has_discussions:", d.get("has_discussions"))
print("  homepage     :", d.get("homepage") or "(空)")
print("  description  :", d.get("description"))
'

echo
echo "=== 外部贡献者（无需认证） ==="
curl -fsS "https://api.github.com/repos/${REPO}/contributors" | python3 -c '
import json, sys
data = json.load(sys.stdin)
if isinstance(data, dict):
    print("  (获取失败)")
else:
    logins = [c["login"] for c in data]
    print("  all          :", logins)
    # 排除作者本人与机器人 —— 它们不是「外部贡献者」。
    external = [x for x in logins if x != "dengmingcong" and not x.endswith("[bot]")]
    print("  external     :", external)
    print("  external_count:", len(external))
'

echo
echo "=== 提醒 ==="
echo "1. watchers 必须读 subscribers_count，不能读 watchers_count（后者是 star 的别名）。"
echo "2. PyPI 项目页的下载量已被官方禁用（返回 -1），必须使用 pypistats。"
echo "3. 下载量含 CI 通胀（GitHub Actions 矩阵每次提交都会产生下载），不等于真人。"
echo "4. 贡献者列表含 github-actions[bot]，统计外部贡献者时必须排除机器人。"
