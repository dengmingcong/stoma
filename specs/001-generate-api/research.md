# 研究结论

## 决策

- 代码生成策略：通过 CLI 从 OpenAPI 预生成
- 输出结构：按功能（feature）为单位的包，包含 router.py 与 models.py
- CLI 命令：`stoma make --spec <openapi.yaml> --out <dir> --feature <name>`

## 理由

- 预生成可最大化运行时性能并提升类型安全
- 按功能的包结构提升可发现性与可维护性
- 使用动词 `make` 加参数符合常见开发者体验模式

## 备选方案评估

- 运行时解析：启动更快，但执行较慢、类型约束弱
- 扁平文件输出：生成更快，但模块化与维护性差
- 使用 `codegen` 命令名：命名清晰，但不如更广泛的 CLI 习惯一致
