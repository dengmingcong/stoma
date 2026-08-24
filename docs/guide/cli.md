# 生成接口

Stoma 提供了 CLI 命令 `stoma` 从 OpenAPI 规范文件自动生成接口代码。

## 命令概览

```
Usage: stoma [OPTIONS] SPEC

  从 OpenAPI 规范生成接口代码。

Arguments:
  SPEC  OpenAPI 规范文件路径（YAML 或 JSON）

Options:
  -o, --out PATH        输出目录路径  [default: .]
  --prefix TEXT         公共路由前缀（如 ``/api/v2``）
  --install-completion  Install completion for the current shell.
  --show-completion     Show completion for the current shell, to copy it or
                        customize the installation.
  --help                Show this message and exit.
```

参数说明：

* `SPEC`：指定 OpenAPI 规范文件路径，当前只支持 `.json`、`.yml` 和 `.yaml` 后缀，且只支持 OpenAPI 3.0 和 3.1。
* `--out` / `-o`：指定输出目录路径，默认为当前目录（`Path(".")`）。
* `--prefix`：为这一批次接口生成公共路径前缀。

## 生成逻辑

简要说明生成过程运行逻辑。

1. 校验输入，确认规范文件存在。
2. 读取规范文件，按声明的 OpenAPI 版本（3.0.x / 3.1.x）派发后续处理。
3. 预处理规范中的引用。
4. 解析为统一的中间表示，规范化每个接口的方法、路径、参数、请求体与响应。
    注意：要求每个操作都有非空的 operationId。
5. 使用 [datamodel-code-generator](https://datamodel-code-generator.koxudaxi.dev/) 生成数据模型，保存到 `models.py`，模型类名由 operationId 派生。
6. 生成 `router.py`，将所有接口汇总到一个路由模板中，`--prefix` 作为公共路径前缀传入。
7. 逐接口渲染。每个接口输出一份以 operationId 蛇形命名的文件，依次完成：
    a. 解析路径、查询、头部参数并生成对应的字段声明。
    b. 按请求体的实际形态（JSON 对象、表单、二进制、纯文本）选择对应的渲染分支。
    c. 按「状态码 + 媒体类型」生成一条响应协议。
8. 为生成的每个文件依次执行 `ruff format` 与 `ruff check --select I,F401 --fix`，若系统未安装 ruff 则跳过。
9. 收集并按类别输出生成过程中的问题：
    * 同一接口的请求体存在多种 Media type：仅采用第一种，作为警告输出并继续。
    * 响应引用的模型不存在于生成的 `models.py`：改用通用响应类型，作为警告输出并继续。
    * 当前不支持的接口形态（如顶层组合 schema 等）：跳过该接口文件的生成并输出错误。

生成的文件目录为：

```
<out>/
├── models.py
├── router.py
└── endpoints/
    ├── __init__.py
    └── <snake_case_operation_id>.py
```

## 完整输出示例

`tests/examples/petstore/app` 下的文件就是用 `stoma` 命令生成的，运行的命令及输出如下：

```shell

```