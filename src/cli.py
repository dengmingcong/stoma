"""Shim for backward compatibility - src.cli now lives at stoma.cli."""

from stoma.cli import app

__all__ = ["app"]
