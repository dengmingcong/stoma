# Generating endpoints

Stoma provides a CLI command, `stoma`, that generates endpoint code from an OpenAPI spec file.

## Command overview

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

Arguments:

* `SPEC`: the path to the OpenAPI spec file. Only `.json`, `.yml` and `.yaml` suffixes are supported, and only OpenAPI 3.0 and 3.1.
* `--out` / `-o`: the output directory. Defaults to the current directory (`Path(".")`).
* `--prefix`: a shared path prefix for the endpoints generated in this batch.

## How generation works

A brief description of the generation process.

1. Validate the input — confirm the spec file exists.
2. Read the spec file and dispatch on the declared OpenAPI version (3.0.x / 3.1.x).
3. Preprocess the references in the spec.
4. Parse into a unified intermediate representation, normalizing the method, path, parameters, request body and responses of every endpoint.
    Note: every operation must have a non-empty operationId.
5. Use [datamodel-code-generator](https://datamodel-code-generator.koxudaxi.dev/) to generate the data models, saved to `models.py`. Model class names are derived from the operationId.
6. Generate `router.py`, collecting all endpoints into one router template, with `--prefix` passed in as the shared path prefix.
7. Render endpoint by endpoint. Each endpoint produces one file named after the snake_case operationId, in this order:
    a. Parse the path, query and header parameters and generate the matching field declarations.
    b. Pick the rendering branch that matches the actual shape of the request body (JSON object, form, binary, plain text).
    c. Generate one response spec per "status code + media type".
8. Run `ruff format` and `ruff check --select I,F401 --fix` on each generated file. If ruff is not installed, this step is skipped.
9. Collect the problems found during generation and report them by category:
    * The request body of one endpoint has multiple media types: only the first is used, reported as a warning, and generation continues.
    * A response references a model that is missing from the generated `models.py`: a generic response type is used instead, reported as a warning, and generation continues.
    * An unsupported endpoint shape (such as a top-level composed schema): the file for that endpoint is skipped and an error is reported.

The generated directory looks like this:

```
<out>/
├── models.py
├── router.py
└── endpoints/
    ├── __init__.py
    └── <snake_case_operation_id>.py
```

## Known limitation: a class name that collides with a Stoma type

The class name of an endpoint is derived from its operationId (`uploadFile` → `UploadFile`).
If the derived class name collides with one of the types Stoma exports (`UploadFile`), the
class definition shadows the imported type:

```python
from stoma import (..., UploadFile)

@router.post("/pet/{petId}/uploadImage", upload_as_multipart=False)
class UploadFile(APIRoute):
    ...
    body: UploadFile   # actually refers to the endpoint class itself, not the file type
```

Importing that module then fails:

```
ValueError: upload_as_multipart=False 要求 body 恰好包含一个 UploadFile 字段，实际有 0 个
```

**The framework does not handle this** — it is up to you to decide how to fix it (rename the
class, change the annotation, or declare it another way). To avoid hitting it, pick
operationIds that don't collide with the type names Stoma exports.

## A full example of the output

The `app/` directory of the [stoma-demo](https://github.com/dengmingcong/stoma-demo) repository was generated with the `stoma` command. The command and its output:

```shell
$ stoma spec.json -o app
→ 生成 models.py
→ 生成 router.py
→ 渲染 GET /users/{user_id}
```
