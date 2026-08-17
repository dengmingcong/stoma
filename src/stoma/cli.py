"""Stoma CLI。

提供 stoma make 命令从 OpenAPI 规范生成接口代码。
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from stoma.exceptions import OpenAPISchemaError
from stoma.openapi.model_generator import generate_models
from stoma.openapi.parser import make_openapi_parser
from stoma.openapi.renderer import make_endpoint_renderer, render_to_file

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
        parser = make_openapi_parser(spec)
        parser.load()
        parser.validate_operation_ids()
        # 必须先调 get_endpoints()，因为 has_json_payloads 由它内部计算。
        raw_spec = parser.raw_spec_dict
        endpoints = parser.get_endpoints()
    except (FileNotFoundError, ValueError, OpenAPISchemaError) as e:
        raise typer.BadParameter(str(e)) from e

    # 决定是否生成 models.py：有 components.schemas 或 paths 中有 JSON payload 即可。
    has_json_payloads = parser.has_json_payloads
    if raw_spec is not None and endpoints:
        schemas = (raw_spec.get("components") or {}).get("schemas") or {}
        if schemas or has_json_payloads:
            generate_models(raw_spec, out / "models.py")

    # 渲染每个 endpoint 的 route.py。
    generated_files: list[Path] = []
    renderer = make_endpoint_renderer(parser.spec_version)

    # 从生成的 models.py 提取所有 class 名字，注入到 renderer
    # renderer 据 此 检 查 {OpId}Response 是否真实存在；不存在的跳过 + 记录
    models_path = out / "models.py"
    if models_path.exists():
        import ast

        tree = ast.parse(models_path.read_text(encoding="utf-8"))
        renderer.available_models = {
            node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
        }

    for endpoint in endpoints:
        file_name, rendered_code = renderer.render(endpoint)
        file_path = render_to_file(
            output_dir=out,
            file_name=file_name,
            rendered_code=rendered_code,
        )
        generated_files.append(file_path)

    if renderer.multi_media_type_endpoints:
        typer.echo("⚠ 以下 endpoint 有多个 media type，已静默使用第一个（其他被忽略）：", err=True)
        for info in renderer.multi_media_type_endpoints:
            typer.echo(f"  - {info['method']} {info['path']}", err=True)
            typer.echo(f"    所有 media type: {', '.join(info['all_media_types'])}", err=True)
            typer.echo(f"    选中: {info['selected_media_type']}", err=True)

    # 打印 Response 模型缺失警告（与 multi-media-type 同模式）
    if renderer.missing_response_models:
        typer.echo("⚠ 以下 endpoint 缺少 Response 模型（已跳过 import + generic）：", err=True)
        for info in renderer.missing_response_models:
            typer.echo(f"  - {info['method']} {info['path']}", err=True)
            typer.echo(f"    缺少: {info['missing_model']}", err=True)

    # 输出结果。
    typer.echo(f"生成 models.py + {len(generated_files)} 个 route 文件到 {out}:")
    for f in generated_files:
        typer.echo(f"  - {f.name}")


if __name__ == "__main__":
    app()
