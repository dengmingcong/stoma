# 数据模型

## 实体

### Endpoint（端点）
- 名称：string
- 方法：枚举（get, post, put, patch, delete）
- 路径：string
- 请求模型：ModelRef
- 响应模型：ModelRef

### RequestModel（请求模型）
- 字段：列表 [Field]
- 必填/可选：逐字段布尔值
- 默认值：逐字段默认值
- 校验：Pydantic v2 规则
- 示例：任意 JSON

### ResponseModel（响应模型）
- 字段：列表 [Field]
- 类型：严格类型策略
- 容错：可配置宽松策略（严格/宽松）

### Field（字段）
- 名称：string
- 类型：Python 类型（兼容 Pydantic）
- 必填：boolean
- 默认值：可选
- 校验器：列表
