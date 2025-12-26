# 快速开始

## 环境准备
1. 安装 Python 3.12 与依赖（含 Playwright）：
   ```bash
   pip install -e .
   playwright install chromium
   ```
2. 进入项目根目录：`cd /Users/dengmingcong/Workspace/stoma`

## 从 OpenAPI 生成代码
1. 运行代码生成命令：
   ```bash
   stoma make --spec api.yaml --out ./generated --feature users
   ```
2. 生成目录参考 FastAPI 分层：`generated/users/{routing.py,params.py,models.py,client.py}`，如需 CLI/模板可放入 `generated/users/codegen/`。

## 使用生成的接口
1. 在测试脚本中导入生成的接口类与模型：
   ```python
   from generated.users.endpoints import GetUsers
   users = GetUsers(token="Bearer xxx")()
   ```
2. 通过 `route_meta = GetUsers.route_meta()` 获取元数据。

## 运行示例测试
1. 执行单元测试：`pytest tests/unit`
2. 执行契约与集成测试：`pytest tests/contract tests/integration`
