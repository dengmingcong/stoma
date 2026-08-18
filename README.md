# Stoma

从 OpenAPI 生成声明式接口测试代码的框架。

## 安装与环境

建议使用 Python 3.11：

```bash
python3 --version
```

```bash
# 核心（pydantic + playwright 运行时；可 import stoma + 用 Client）
pip install stoma

# 加 CLI 工具 `stoma make`
pip install stoma[cli]

# 加测试基础设施（pytest + FastAPI mock server）
pip install stoma[test]

# 开发（全部 + 类型/lint）
pip install stoma[dev]
```

## 生成代码

```bash
stoma make --spec specs/001-generate-api/contracts/openapi.yaml --out src/example
```

## 运行测试（占位）

```bash
pytest -q
```

## 文档

更详细的文档参见 [docs/README.md](./docs/README.md)。

## 目录结构

```
src/
	stoma/
		__init__.py
		cli.py
		client.py
		routing.py
		param_functions.py
		params.py
		exceptions.py
		dependencies/
		openapi/
```

