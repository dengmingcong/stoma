"""``datamodel-code-generator`` 的 Python API 封装。

stoma 的 ``make`` 命令在预处理 spec 后调用本模块生成 ``models.py``，
通过固化 :func:`generate` 的参数确保所有 spec 走相同的输出约定
（Pydantic v2、snake_case 字段、``$ref`` 解析、操作 ID 命名）。

参考：
- https://github.com/koxudaxi/datamodel-code-generator
- https://datamodel-code-generator.koxudaxi.dev/
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from datamodel_code_generator import (
    InputFileType,
    OpenAPIScope,
    PythonVersion,
    generate,
)
from datamodel_code_generator.enums import DataModelType


def generate_models(spec_dict: dict[str, Any], output_path: Path) -> None:
    """调用 ``datamodel-code-generator`` 生成 Pydantic v2 模型到 ``output_path``。

    输入：解析后的 OpenAPI 规范字典。
    输出：单个 ``models.py``，包含 spec 中所有 ``$ref`` schemas + inline
    objects（带 HTTP method + path 派生的 PascalCase 类名）。

    :param spec_dict: 解析后的 OpenAPI 规范字典。
    :param output_path: ``models.py`` 的输出路径。父目录如不存在会自动创建。
    :raise RuntimeError: ``datamodel-code-generator`` 调用失败且未产出文件。
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        generate(
            input_=spec_dict,
            output=output_path,
            input_file_type=InputFileType.OpenAPI,
            output_model_type=DataModelType.PydanticV2BaseModel,
            target_python_version=PythonVersion.PY_312,
            snake_case_field=True,
            use_double_quotes=True,
            use_union_operator=True,
            openapi_scopes=[OpenAPIScope.Schemas, OpenAPIScope.Paths],
        )
    except Exception as e:
        msg = f"datamodel-code-generator 调用失败: {e}"
        raise RuntimeError(msg) from e

    if not output_path.exists():
        msg = f"datamodel-code-generator 未生成文件: {output_path}"
        raise RuntimeError(msg)
