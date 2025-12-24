---
applyTo: '**/*.py'
---
# 常量编码规范

## 命名

常量名应该使用全大写，多个单词使用下划线分割。

```python
# ✅ Good
CONSTANT_NAME: str = "value"
```

```python
# ❌ Bad
# 常量名使用小写。
constant_name: str = "value"
```

## 类型注解

应该为常量名做类型注解并确保类型准确。

```python
# ✅ Good
CONSTANT_NAME: str = "value"
```

```python
# ❌ Bad
# 未使用类型注解。
CONSTANT_NAME = "value"
 
# 类型注解和实际类型不匹配。
CONSTANT_NAME: int = "value"
```

## 注释

必要时，应该以块注释对常量进行补充说明。

```python
# ✅ Good
# 这是对常量的注释示例。
CONSTANT_NAME: str = "value"
```

## 空行

相关联的常量应该放在一起，相互之间不应有空行，如果常量有注释，也不应有空行。不相关联的常量之间应该用一个空行隔开。

```python
# ✅ Good
# 这是一个和下面的常量不相关联的常量。
DEFAULT_VIZ_TYPE = "table"
 
# 下面的常量是相关联的，相互之间不应有空行，但和上面的常量之间有一个空行。
ROW_LIMIT = 50000
# 这是另一个注释
SAMPLES_ROW_LIMIT = 1000
NATIVE_FILTER_DEFAULT_ROW_LIMIT = 1000
# 这还是一个注释。
FILTER_SELECT_ROW_LIMIT = 10000
```

## 常量类

如果多个常量具有相关性且需要使用统一的前缀，应该定义一个类包含这些常量，并且应该为类添加文档字符串，文档字符串可以不包含类属性。

类属性名命名规范和普通常量一致。

```python
# ✅ Good
class DurationCode:
    """时间范围代码。"""
    YEAR: str = "y"
    MONTH: str = "m"
    WEEK: str = "w"
```

```python
# ❌ Bad
# 重复使用相同的前缀。
DURATION_CODE_YEAR: str = "y"
DURATION_CODE_MONTH: str = "m"
DURATION_CODE_WEEK: str = "w"
 
# 类属性名使用小写。
class DurationCode:
    """时间范围代码。"""
    year: str = "y"
    month: str = "m"
    week: str = "w"
```

类定义应该放在普通常量定义之后。

```python
# ✅ Good
# 这是普通常量
CONSTANT_VAR: str = "value"
 
# 这是另一个普通常量。
ANOTHER_CONSTANT_VAR: int = 1
 
# 这是常量类，应该放在普通常量后面
class DurationCode:
    """时间范围代码。"""
    YEAR: str = "y"
    MONTH: str = "m"
    WEEK: str = "w"
```