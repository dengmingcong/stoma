"""Stoma CLI。

提供 stoma make 命令从 OpenAPI 规范生成接口代码。
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from src.openapi.model_generator import generate_models
from src.openapi.parser import OpenAPIParser, OpenAPISchemaError
from src.openapi.renderer import EndpointRenderer, render_to_file

app = typer.Typer(
    help="Stoma - OpenAPI 接口代码生成工具",
    no_args_is_help=True,
)


@app.command()
def make(
    spec: Annotated[Path, typer.Argument(help="OpenAPI 规范文件路径（YAML 或 JSON）")],
    out: Annotated[Path, typer.Option("--out", "-o", help="输出目录路径")] = Path("."),
) -> None:
    """从 OpenAPI 规范生成接口代码。

    读取 OpenAPI 规范文件，生成一份 ``models.py``（由
    ``datamodel-code-generator`` 产出）+ 每个 endpoint 一份路由文件
    （引用 ``models.py`` 中的类型）。
    """
    # 校验 spec 文件。
    if not spec.exists():
        raise typer.BadParameter(f"文件不存在: {spec}")
    if not spec.is_file():
        raise typer.BadParameter(f"不是文件: {spec}")

    # 确保输出目录可写。
    try:
        out.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise typer.BadParameter(f"无法创建输出目录: {out}") from e

    # 解析 OpenAPI 规范。
    try:
        parser = OpenAPIParser(spec)
        parser.load()
        parser.validate_operation_ids()
        # 必须先调 get_endpoints()，因为 has_payloads 由它内部计算。
        raw_spec = parser.raw_spec_dict
        endpoints = parser.get_endpoints()
    except (FileNotFoundError, ValueError, OpenAPISchemaError) as e:
        raise typer.BadParameter(str(e)) from e

    # 决定是否生成 models.py：有 components.schemas 或 paths 中有 payload 即可。
    has_payloads = parser.has_payloads
    if raw_spec is not None and endpoints:
        schemas = (raw_spec.get("components") or {}).get("schemas") or {}
        if schemas or has_payloads:
            generate_models(raw_spec, out / "models.py")

    # 渲染每个 endpoint 的 route.py。
    generated_files: list[Path] = []
    renderer = EndpointRenderer()
    for endpoint in endpoints:
        file_name, rendered_code = renderer.render(endpoint)
        file_path = render_to_file(
            output_dir=out,
            file_name=file_name,
            rendered_code=rendered_code,
        )
        generated_files.append(file_path)

    # 输出结果。
    typer.echo(f"生成 models.py + {len(generated_files)} 个 route 文件到 {out}:")
    for f in generated_files:
        typer.echo(f"  - {f.name}")


if __name__ == "__main__":
    app()
