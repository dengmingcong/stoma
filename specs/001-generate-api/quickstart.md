# 快速开始

## 从 OpenAPI 生成代码

stoma make --spec openapi.yaml --out src/example --feature users

## 运行测试（示例）

python -m stoma.run --suite default

## 生成的包结构

src/example/users/
├── __init__.py
├── router.py
└── models.py

## 说明

- 使用 Pydantic v2 进行类型定义与校验
- 使用 Playwright 作为 HTTP 客户端
