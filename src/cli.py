"""Stoma CLI。

提供 stoma make 命令从 OpenAPI 规范生成接口代码。
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

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

    读取 OpenAPI 规范文件，为每个 endpoint 生成独立的 .py 文件，
    包含 route 类和内嵌的 model。
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
        parser.validate()
    except (FileNotFoundError, ValueError, OpenAPISchemaError) as e:
        raise typer.BadParameter(str(e)) from e

    # 获取所有 endpoint 并渲染。
    renderer = EndpointRenderer()
    endpoints = parser.get_endpoints()

    generated_files: list[Path] = []
    for endpoint in endpoints:
        rendered = renderer.render(
            operation_id=endpoint["operation_id"],
            method=endpoint["method"],
            path=endpoint["path"],
            parameters=endpoint["parameters"],
            request_body=endpoint["request_body"],
            responses=endpoint["responses"],
            summary=endpoint["summary"],
            description=endpoint["description"],
        )
        file_path = render_to_file(
            output_dir=out,
            operation_id=endpoint["operation_id"],
            rendered_code=rendered,
        )
        generated_files.append(file_path)

    # 输出结果。
    typer.echo(f"生成 {len(generated_files)} 个文件到 {out}:")
    for f in generated_files:
        typer.echo(f"  - {f.name}")


if __name__ == "__main__":
    app()
