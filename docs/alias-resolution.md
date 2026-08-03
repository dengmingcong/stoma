# Pydantic Alias 机制详解

> 基于 Pydantic v2 源码分析（`/Users/dengmingcong/Workspace/pydantic`）
>
> 参考：https://pydantic.dev/docs/validation/latest/concepts/alias/

---

## 一、alias 的种类

| 参数 | 作用范围 | 说明 |
|------|---------|------|
| `alias` | 验证 + 序列化 | 默认的别名，字段用 alias 名做 key 验证和序列化 |
| `validation_alias` | 仅验证 | 仅在验证时使用的别名 |
| `serialization_alias` | 仅序列化 | 仅在序列化时使用的别名 |
| `alias_generator` | 配置级 | `model_config` 中设置，`Callable[str] -> str`，自动生成上述三个 alias |
| `AliasPath` | 仅 `validation_alias` | 嵌套路径，如 `AliasPath('outer', 'inner')` |
| `AliasChoices` | 仅 `validation_alias` | 备选别名列表，如 `AliasChoices('a', 'b', AliasPath('x', 'y'))` |

---

## 二、`Field()` 调用时：alias 的相互兜底

**源码位置**：`pydantic/fields.py:1349-1353`

### 兜底规则

当 `Field()` 函数执行时，以下赋值**按顺序**发生：

```python
# 1. 各自接收用户传入的值（无则为 None）
self.alias = kwargs.pop('alias', None)
self.validation_alias = kwargs.pop('validation_alias', None)
self.serialization_alias = kwargs.pop('serialization_alias', None)

# 2. 互相兜底（仅当目标为 None 时）
if serialization_alias in (_Unset, None) and isinstance(alias, str):
    serialization_alias = alias       # 只有 alias → 拷贝到 serialization_alias

if validation_alias in (_Unset, None):
    validation_alias = alias          # 只有 alias → 拷贝到 validation_alias
```

### 结果对照表

| `Field()` 调用 | `alias` | `validation_alias` | `serialization_alias` |
|---|---|---|---|
| `Field()` | `None` | `None` | `None` |
| `Field(alias="A")` | `"A"` | `"A"` | `"A"` |
| `Field(validation_alias="V")` | `None` | `"V"` | `None` |
| `Field(serialization_alias="S")` | `None` | `None` | `"S"` |
| `Field(alias="A", validation_alias="V")` | `"A"` | `"V"` | `"A"` |
| `Field(alias="A", serialization_alias="S")` | `"A"` | `"A"` | `"S"` |
| `Field(validation_alias="V", serialization_alias="S")` | `None` | `"V"` | `"S"` |
| `Field(alias="A", validation_alias="V", serialization_alias="S")` | `"A"` | `"V"` | `"S"` |

### `alias_priority` 的确定

**源码位置**：`pydantic/fields.py:259`

```python
alias_is_set = any(alias is not None for alias in (self.alias, self.validation_alias, self.serialization_alias))
self.alias_priority = kwargs.pop('alias_priority', None) or 2 if alias_is_set else None
```

| 条件 | `alias_priority` |
|------|-----------------|
| 设置了任意一个 alias（alias/validation_alias/serialization_alias） | `2` |
| 什么都没设置 | `None` |

**`alias_priority=2` 的含义**：generator **禁止**覆盖任何已设置的 alias。

---

## 三、模型类构建时：`alias_generator` 的写入

**源码位置**：`pydantic/_internal/_fields.py:140-187`

### 触发时机

Python 执行 `class X(BaseModel): ...` 时，`ModelMetaclass.__new__` 依次调用：

1. `set_model_fields()`（`_model_construction.py:249`）
2. `collect_model_fields()`（`_fields.py:223`）
3. `update_field_from_config()`（`_fields.py:190`）→ `_apply_alias_generator_to_field_info()`

### `_apply_alias_generator_to_field_info` 逻辑

```python
# 仅当 alias_priority 是 None 或 <= 1 时，generator 才被允许写入
if (
    field_info.alias_priority is None
    or field_info.alias_priority <= 1
    or field_info.alias is None
    or field_info.validation_alias is None
    or field_info.serialization_alias is None
):
    alias, validation_alias, serialization_alias = generator(field_name)

    # priority=None → 升级为 1（generator 写入模式）
    if field_info.alias_priority is None or field_info.alias_priority <= 1:
        field_info.alias_priority = 1

    # priority=1 → generator 写入所有三个 alias
    if field_info.alias_priority == 1:
        field_info.serialization_alias = get_first_not_none(serialization_alias, alias)
        field_info.validation_alias = get_first_not_none(validation_alias, alias)
        field_info.alias = alias

    # 任何 alias 仍为 None → 用 generator 结果补上
    if field_info.alias is None:
        field_info.alias = alias
    if field_info.serialization_alias is None:
        field_info.serialization_alias = ...
    if field_info.validation_alias is None:
        field_info.validation_alias = ...
```

### 实际行为总结

| 场景 | `alias` | `validation_alias` | `serialization_alias` |
|------|---------|------------------|---------------------|
| `Field(alias="A")` + generator | `"A"` | `"A"` | `"A"` |
| 无 `Field` + generator | generator 输出 | generator 输出 | generator 输出 |
| `Field(validation_alias="V")` + generator | generator 输出 | `"V"` | generator 输出 |
| `Field(alias="A")` + generator（`alias_priority=2`）| `"A"` | `"A"` | `"A"` |

### `AliasPath` / `AliasChoices` 的特殊性

两者**只能**作为 `validation_alias` 的值，**不能**被 `alias_generator` 覆盖（因为 generator 输出的是 `str`，不是 `AliasPath`/`AliasChoices`）。

```python
Field(validation_alias=AliasPath('outer', 'inner'))
# model_fields['x'].alias          → None  （generator 无法写入 AliasPath）
# model_fields['x'].validation_alias → AliasPath('outer', 'inner')
```

---

## 四、完整生命周期图

```
用户写 Field(...)
        │
        ├─ alias / validation_alias / serialization_alias 各自接收用户值
        ├─ 互相兜底（alias → validation_alias, alias → serialization_alias）
        └─ alias_priority 确定：设了任意 alias → 2，都没设 → None
        │
        ▼
   ModelMetaclass.__new__  (class X(BaseModel): ...)
        │
        ├─ set_model_fields()
        │     └─ collect_model_fields()
        │           └─ update_field_from_config()  ← alias_generator 介入点
        │                 └─ _apply_alias_generator_to_field_info()
        │                       │
        │                       ├─ alias_priority == 2 ?  → 完全跳过
        │                       └─ alias_priority is None ? → generator 写入
        │
        └─ complete_model_class()  ← schema 生成、验证/序列化钩子注册
```

---

## 五、`model_field.alias` 在 stoma 中读到什么

stoma 的 `ModelField.alias`（`src/dependencies/models.py:30-44`）：

```python
@property
def alias(self) -> str:
    if self.field_info.alias:
        return self.field_info.alias
    return self.name
```

它只读 `field_info.alias`，不读 `validation_alias` / `serialization_alias`。

所以 stoma `Client.send` 在收集 HTTP 参数时：

| 场景 | `Client.send` 使用的 key |
|------|------------------------|
| `Field(alias="X")` | `"X"` |
| `Field(validation_alias="V")` | 字段名（`alias` 为 None 回退） |
| `Field(serialization_alias="S")` | 字段名 |
| `Field(validation_alias=AliasPath('a','b'))` | 字段名 |
| `alias_generator` 生成 | generator 输出（`alias` 有值时） |

**核心结论**：如果只想在 HTTP 请求中使用 alias 名（序列化），但允许 Python 代码中用字段名验证，应该用 `Field(alias=...)`；如果想让 `Client.send` 在验证和序列化时都感知同一个 alias 名，必须让 `alias` 有值（显式设置或通过 generator 生成）。