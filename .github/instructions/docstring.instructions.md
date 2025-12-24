---
applyTo: '**/*.py'
---
# 文档字符串（Docstring）规范

使用 reStructuredText 作为文档字符串的格式。

## 通用规范

### 单行文档字符串

单行文档字符串的所有内容应该放在同一行，包括起始的三引号和结尾的三引号，以句号结尾。

```python
# ✅ Good
"""单行文档字符串示例。"""
```

```python
# ❌ Bad
"""
引号和文字各占一行。
"""

"""结尾的引号另起了一行。
"""
```

### 多行文档字符串

多行文档字符串应该由一行概述开始，然后留一空行，再接更详细的描述。作为结尾的三引号应该单独成行，不应紧跟在最后一句文本后面。

```python
# ✅ Good
"""一行概述。
 
和摘要之间留一空行，然后继续写更详细的描述，也应该以句号结尾。
"""
```

```python
# ❌ Bad
"""一行摘要。
没有空一行就开始写详细的描述。
"""
 
"""一行摘要。
 
结尾的三引号没有单独成行。"""
```

## 模块

Python 中一个文件被称为一个模块，模块可以包含文档字符串来描述文件内容。

```python
# ✅ Good
"""模块的一行概述，以句号结尾。
 
如果需要对模块做进一步说明，空一行后再详细描述。
"""
```

测试文件的模块级文档字符串并非必须，只有在需要提供附加信息时才应该包含。并不提供任何新信息的文档字符串不应被使用。

```python
# ❌ Bad
"""Tests for foo.bar."""
```

## 函数和方法

> 本节使用「函数」来说明，除非有特别说明，函数的规则也适用于方法、生成器和 `@property` 装饰器。

文档字符串应该提供足够的信息，使人无需阅读函数代码就可以调用该函数。  
它应该描述函数的调用语法和语义，但通常不应包含实现细节 – 除非这些细节与函数的使用方式息息相关。

函数中下面这些部分应该以字段列表（`Field List`）的形式书写，主流编辑器可以用更加突出的方式呈现。

### 参数

以 `:param <param name>:` 为字段标记来描述参数，字段值为文字描述，以句号结尾。  
以 `:type <param name>:` 为字段标记来描述参数类型，字段值为参数类型，不应添加句号。

```python
# ✅ Good
def function_with_types_in_docstring(arg1, arg2):
    """函数的单行概述。
 
    更详细的描述可以在这里添加。
 
    :param arg1: 第一个参数的描述。
    :type arg1: int
    :param arg2: 第二个参数的描述。
    :type arg2: str
    """
```

```python
# ❌ Bad
def function_with_types_in_docstring(arg):
    """函数的单行概述。
 
    :param arg: 参数的描述没有添加句号，类型又添加了句号
    :type arg: int。
    """
```

如果使用 PEP484 的方式为参数做了类型注解，文档字符串应该省略参数类型的说明。

应该优先采用代码类型注解，而不应优先在文档字符串中标注参数类型，这样编辑器能更好地推测代码。

```python
# ✅✅  Better
def function_with_pep484_type_annotations(arg1: int, arg2: str):
    """函数的单行概述。
 
    更详细的描述可以在这里添加。
 
    :param arg1: 第一个参数的描述。
    :param arg2: 第二个参数的描述。
    """
```

函数的每一个参数都应该在文档字符串中说明，但不应包含方法的 `self` 参数。

若函数接受 `*arg`（可变位置参数）或 `**kwargs`（任意关键字参数），应该分别用 `:param *arg:` 和 `:param **kwargs:` 表示。

```python
# ✅ Good
def function_with_unspecified_number_args(
    param1: str, param2: int = 1, *args, **kwargs
):
    """函数概述。
 
    :param param1: 第一个参数的描述。
    :param param2: 第二个参数的描述。
    :param *args: 可变位置参数。
    :param **kwargs: 任意关键字参数。
    """
```

### 返回值

以 `:return:` 为字段标记描述返回值，以 `:rtype:` 为字段标记描述返回类型。  
如果函数仅返回 `None`，则应该省略对返回值的说明。

```python
# ✅ Good
def function_with_returns(arg1: int, arg2: str):
    """函数的单行概述。
 
    更详细的描述可以在这里添加。
 
    :param arg1: 第一个参数的描述。
    :param arg2: 第二个参数的描述。
    :return: 返回值的描述。
    :rtype: bool
    """
```

和函数参数类似，如果使用 PEP484 的方式为返回值做了类型注解，文档字符串应该省略返回值类型的说明。

应该优先采用代码类型注解，而不应优先在文档字符串中标注返回值类型。

```python
# ✅✅  Better
def function_with_return(arg1: int, arg2: str) -> bool:
    """函数的单行概述。
 
    更详细的描述可以在这里添加。
 
    :param arg1: 第一个参数的描述。
    :param arg2: 第二个参数的描述。
    :return: 返回值的描述。
    """
```

### 异常

以 `:raise <Error Type>:` 为字段标记描述异常，列出所有与函数相关的异常。

```python
# ✅ Good
def function_with_exceptions(param1: str, param2: str):
    """函数概述。
 
    :param param1: 第一个参数的描述。
    :param param2: 第二个参数的描述。
    :raise ValueError: 如果 ``param2`` 等于 ``param1``。
    """
    if param1 == param2:
        msg = "param1 必须不等于 param2。"
        raise ValueError(msg)
    return True
```

## 类

在类定义下方应该使用文档字符串描述该类。

以 `:var <attribute name>:` 为字段标记描述公共属性，字段值为文字描述，以句号结尾。  
以 `:vartype <attribute name>:` 为字段标记描述属性类型，字段值为类型，不应添加句号。

如果类有 `__init__` 构造方法，和函数一样，以 `:param <param name>:` 为字段标记来描述参数，以 `:type <param name>:` 为字段标记来描述参数类型。

```python
# ✅ Good
class ExampleClass:
    """对类的概述。
 
    更详细的描述可以在这里添加。
 
    :var attr1: 第一个属性的描述。
    :vartype attr1: str
    :var attr2: 第二个属性的描述。
    :vartype attr2: int
    """
 
    def __init__(self, param1: str, param2: int):
        """对类的 __init__ 方法的概述。
 
        更详细的描述可以在这里添加。
 
        :param param1: 第一个参数的描述。
        :param param2: 第二个参数的描述。
        """
        self.attr1 = param1
        self.attr2 = param2
```

使用 `@property` 装饰器创建的属性应该在 property 的 `getter` 方法中说明。

```python
# ✅ Good
class ExampleClass:
    """对类的概述。"""
 
    @property
    def readwrite_property(self) -> list[str]:
        """同时包含 getter 和 setter 的 property，只在 getter 方法中添加文档字符串对属性说明。
 
        如果有其他需要着重说明的事项，在此继续添加。
        """
        return ["readwrite_property"]
 
    @readwrite_property.setter
    def readwrite_property(self, value):
        _ = value
```

类的文档字符串中不应重复非必需的信息，比如说明该类是一个类。

```python
# ✅ Good
class CheeseShopAddress:
    """Cheese Shop 的地址。"""
 
class OutOfCheeseError(Exception):
    """没有奶酪了。"""
```

```python
# ❌ Bad

class CheeseShopAddress:
    """描述 Cheese Shop 地址的一个类。"""
 
class OutOfCheeseError(Exception):
    """当没有奶酪时抛出的异常。"""
```

## 块注释（Block Comments）

如果你觉得在下次代码审查时需要解释这部分代码，那么现在就应该加上注释。

在需要注释的代码前以 `#` 开头，空一格后开始写注释，并以句号结尾。

```python
# ✅ Good
# 这是对代码的注释，以句号结尾。
if some_value == 0:
```

```python
# ❌ Bad
# 这是对代码的注释，未以句号结尾
if some_value == 0:
```

块注释可以包含多行：

```python
# ✅ Good
# 这是代码注释的第一行，
# 这是注释的第二行，以句号结尾。
if some_value == 0:
```

## 完整示例

```python
# ✅ Good
"""文档字符串（docstring）规范的示例。
 
一个段落可以包含多行，
但是必须左侧对齐。
 
使用 ``Example`` 为模块、函数、类或方法添加示例。
 
Example::
 
    $ python example.py
"""
 
 
def function_with_types_in_docstring(param1, param2):
    """文档字符串中包含类型的示例。
 
    更好的方式是使用 :pep:`484` 的方式对参数和返回值进行类型注解。
    如果已经对参数和返回值做了类型注解，则不应在文档字符串中重复类型信息。
 
    :param param1: 对参数的描述应该以句号结尾，参数类型句尾不应添加句号。
    :type param1: int
    :param param2: 第二个参数的描述。
    :type param2: str
    :return: 对返回值的描述，以句号结尾。
    :rtype: bool
    """
    return True
 
 
def function_with_pep484_type_annotations(param1: int, param2: str) -> bool:
    """使用 PEP 484 类型注解的示例函数。
 
    优先使用 PEP 484 的方式对参数和返回值进行类型注解，
    这样编辑器可以更好地理解参数和返回值的类型。
 
    :param param1: 第一个参数的描述。
    :param param2: 第二个参数的描述。
 
    :return: 返回值。True 表示成功，False 表示失败。
    """
 
 
def module_level_function(param1, param2=None, *args, **kwargs):
    """完整的函数文档字符串示例。
 
    参数
        以 ``:param <param name>:`` 为字段标记描述参数，字段值为文字描述，以句号结尾。
        以 ``:type <param name>:`` 为字段标记描述参数类型，字段值为类型，句尾不应添加句号。
        如果使用 :pep:`484` 的方式对参数和返回值进行了类型注解，则不应在文档字符串中重复类型信息。
 
    可变参数
        如果函数接受可变位置参数 ``*args`` 或任意关键字参数 ``**kwargs``，
        应该分别用 ``:param *args:`` 和 ``:param **kwargs:`` 进行描述。
 
    参数默认值
        如果需要对默认值说明，在句号后以类似于 ``default: 'text'`` 的形式说明。
        默认值后面不应添加句号（句号会干扰对默认值的判断，不知道是不是默认值的一部分）。
        默认值应该以行内代码示例的方式指明，并且应该以 repr 的输出的形式表示。
 
    返回值
        以 ``:return:`` 为字段标记描述返回值，以 ``:rtype:`` 为字段标记描述返回类型。如果函数仅返回 ``None``，则应该省略。
        如果使用 PEP484 的方式为返回值做了类型注解，文档字符串应该省略返回值类型的说明。
 
    异常
        以 ``:raise <Error Type>:`` 为字段标记描述异常，列出所有与函数相关的异常。
 
    :param param1: 第一个参数的描述，一个段落
        可以跨多行，但必须相对于字段标记有缩进量。
 
        还可以包含多个段落，第二个段落必须和字段标记下第一行左侧对齐。
 
        还可以包含列表和子列表：
 
        - 列表项 1
 
            * 子列表项 1
            * 子列表项 2
 
        - 列表项 2
 
        还可以包含代码::
 
            def example_function():
                pass
 
    :type param1: str
    :param param2: 第二个参数的描述。default: ``None``
    :type param2: str, optional
    :param *args: 对可变位置参数的描述。
    :param **kwargs: 对任意关键字参数的描述。
    :return:
        成功时返回 True，失败时返回 False。
 
        可以通过代码块添加返回值示例::
 
            {
                "param1": "foo",
                "param2": "bar"
            }
 
    :rtype: bool
    :raise ValueError: 如果 `param2` 等于 `param1`，则抛出此异常。
    """
    if param1 == param2:
        msg = "param1 may not be equal to param2"
        raise ValueError(msg)
    return True
 
 
def example_generator(n):
    """生成器包含 ``Yields`` 部分而不是 ``Returns`` 部分。
 
    Examples::
 
        >>> print([i for i in example_generator(4)])
        [0, 1, 2, 3]
 
    :param n: 要生成的范围的上限，生成的范围为从 0 到 `n` - 1。
    :type n: int
    :return: 从 0 到 `n` - 1 范围的下一个数字。
    :rtype: int
    """
    yield from range(n)
 
 
class ExampleErrorOutOfCheeseError(Exception):
    """奶酪不足。"""
 
    pass
 
 
class ExampleClass:
    """类的一行概述。
 
    如果类有公共属性，以 ``:var <attribute name>:`` 为字段标记描述属性，字段值为文字描述，以句号结尾。
    以 ``:vartype <attribute name>:`` 为字段标记描述属性类型，字段值为类型，不应添加句号。
 
    如果类有 ``__init__`` 构造方法，和函数一样，以 ``:param <param name>:`` 为字段标记来描述参数，
    以 ``:type <param name>:`` 为字段标记来描述参数类型。
 
    使用 ``@property`` 装饰器创建的属性应该在 property 的 getter 方法中说明。
 
    :var attr1: 第一个属性的描述。
    :vartype attr1: str
    :var attr2: 第二个属性的描述。
    :vartype attr2: int, optional
    """
 
    def __init__(self, param1, param2, param3):
        """类的 ``__init__`` 方法示例。
 
        .. note::
            不应在参数部分中包含 ``self`` 参数。
 
        :param param1: 第一个参数的描述。
        :type param1: str
        :param param2: 第二个参数的描述。
        :type param2: int, optional
        :param param3: 第三个参数的描述。
        :type param3: list(str)
        """
        self.attr1 = param1
        self.attr2 = param2
        self.attr3 = param3
 
    @property
    def readwrite_property(self) -> list[str]:
        """同时具有 getter 和 setter 的属性，应该只在 getter 方法中进行文档说明。"""
        return ["readwrite_property"]
 
    @readwrite_property.setter
    def readwrite_property(self, value):
        _ = value
 
    def example_method(self, param1, param2):
        """类方法和普通函数使用类似的文档字符串格式。
 
        .. note::
            不应在参数部分中包含 ``self`` 参数。
 
        :param param1: 第一个参数的描述。
        :type param1: str
        :param param2: 第二个参数的描述。
        :type param2: str
        :return: 成功时返回 True，失败时返回 False。
        :rtype: bool
        """
        return True
```