"""Stoma CLI。

提供 stoma make 命令从 OpenAPI 规范生成接口代码。
"""

from __future__ import annotations

import ast
import shutil
import subprocess
from pathlib import Path
from typing import Annotated

import typer

from stoma.exceptions import OpenAPISchemaError
from stoma.openapi.model_generator import generate_models
from stoma.openapi.parser import make_openapi_parser
from stoma.openapi.renderer import (
    GenerationError,
    GenerationErrorKind,
    make_endpoint_renderer,
    render_to_file,
)

app = typer.Typer(
    help="Stoma - OpenAPI 接口代码生成工具",
    no_args_is_help=True,
)


@app.command()
def make(
    spec: Annotated[Path, typer.Argument(help="OpenAPI 规范文件路径（YAML 或 JSON）")],
    out: Annotated[Path, typer.Option("--out", "-o", help="输出目录路径")] = Path("."),
    prefix: Annotated[str | None, typer.Option("--prefix", help="公共路由前缀（如 ``/api/v2``）")] = None,
) -> None:
    """从 OpenAPI 规范生成接口代码。"""
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
            typer.echo("→ 生成 models.py", err=True)
            generate_models(raw_spec, out / "models.py")
            if shutil.which("ruff") is not None:
                subprocess.run(
                    ["ruff", "format", str(out / "models.py")],
                    check=False,
                    capture_output=True,
                    timeout=30,
                )

    # 渲染每个 endpoint 的 route.py。
    generated_files: list[Path] = []
    renderer = make_endpoint_renderer(parser.spec_version)

    # 从生成的 models.py 提取所有 class 名字，注入到 renderer
    # renderer 据 此 检 查 {OpId}Response 是否真实存在；不存在的跳过 + 记录
    models_path = out / "models.py"
    if models_path.exists():
        tree = ast.parse(models_path.read_text(encoding="utf-8"))
        renderer.available_models = {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}

    router_template = renderer.env.get_template("router.py.jinja2")
    router_code = router_template.render(prefix=prefix or "")
    typer.echo("→ 生成 router.py", err=True)
    render_to_file(
        output_dir=out,
        file_name="router.py",
        rendered_code=router_code,
        enable_ruff=True,
    )

    endpoints_init_path = out / "endpoints" / "__init__.py"
    endpoints_init_path.parent.mkdir(parents=True, exist_ok=True)
    endpoints_init_path.write_text("# endpoints package marker\n", encoding="utf-8")

    for endpoint in endpoints:
        try:
            typer.echo(f"→ 渲染 {endpoint.method} {endpoint.path}", err=True)
            file_name, rendered_code = renderer.render(endpoint)
            file_path = render_to_file(
                output_dir=out / "endpoints",
                file_name=file_name,
                rendered_code=rendered_code,
                enable_ruff=True,
            )
            generated_files.append(file_path)
        except OpenAPISchemaError as e:
            # 可允许的 spec 不支持或边缘 case（type_mapping.py:107/133/138/143/148,
            # renderer.py:273/457）→ 跳过该 endpoint，收集到 renderer.errors
            renderer.errors.append(
                GenerationError(
                    method=endpoint.method,
                    path=endpoint.path,
                    kind=GenerationErrorKind.SCHEMA_UNSUPPORTED,
                    message=str(e),
                )
            )
        # 显式不捕获以下异常：
        # - TypeError（flatten_body_fields:101）→ 内部 bug，立即终止 CLI
        # - ValueError → 内部 bug，立即终止 CLI

    if renderer.errors:
        by_kind: dict[GenerationErrorKind, list[GenerationError]] = {}
        for err in renderer.errors:
            by_kind.setdefault(err.kind, []).append(err)

        kind_titles = {
            GenerationErrorKind.MULTI_MEDIA_TYPE: "以下 endpoint 有多个 media type（已用第一个）",
            GenerationErrorKind.MISSING_RESPONSE_MODEL: "以下 endpoint 缺少 Response 模型（已用 generic）",
            GenerationErrorKind.SCHEMA_UNSUPPORTED: "以下 endpoint 生成失败（spec 不被支持）",
        }

        for kind in GenerationErrorKind:
            if kind not in by_kind:
                continue
            typer.echo(f"⚠ {kind_titles[kind]}：", err=True)
            for err in by_kind[kind]:
                typer.echo(f"  - {err.location}", err=True)
                typer.echo(f"    {err.message}", err=True)

        # 只有 SCHEMA_UNSUPPORTED（实际未生成文件）才 exit 1
        if by_kind.get(GenerationErrorKind.SCHEMA_UNSUPPORTED):
            raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
