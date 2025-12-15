# Stoma

从 OpenAPI 生成声明式接口测试代码的框架。

## 安装与环境

建议使用 Python 3.11：

```bash
python3 --version
pip install -e .
```

## 生成代码

```bash
stoma make --spec specs/001-generate-api/contracts/openapi.yaml --out src/example --feature users
```

## 运行测试（占位）

```bash
pytest -q
```

## 目录结构

```
src/
	example/
		users/
			router.py
			models.py
```

