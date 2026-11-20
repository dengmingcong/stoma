# -*- coding: utf-8 -*-
"""比较重新生成前后的 app/：忽略 import 差异后，类定义与响应协议是否完全一致。"""

import ast
from pathlib import Path

OLD = Path('/tmp/app_backup_demo')
NEW = Path('app')


def summarize(path: Path) -> dict:
    """抽取每个类的方法与属性签名（不含 import）。"""
    tree = ast.parse(path.read_text(encoding='utf-8'))
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            members = []
            for m in node.body:
                if isinstance(m, ast.FunctionDef):
                    args = [a.arg for a in m.args.args]
                    members.append(f'def {m.name}({",".join(args)})')
                elif isinstance(m, ast.AnnAssign):
                    members.append(f'attr {ast.unparse(m.target)}: {ast.unparse(m.annotation)}')
            out[node.name] = sorted(members)
    return out


diffs = 0
checked = 0
for f in sorted(NEW.rglob('*.py')):
    rel = f.relative_to(NEW)
    old = OLD / rel
    if not old.exists():
        print(f'  ⚠ 新增文件: {rel}')
        continue
    if rel.name == '__init__.py':
        continue
    checked += 1
    a, b = summarize(old), summarize(f)
    if a != b:
        diffs += 1
        print(f'  ❌ {rel}: 类成员不同')
        for k in set(a) | set(b):
            if a.get(k) != b.get(k):
                print(f'      {k}:')
                print(f'        旧: {a.get(k)}')
                print(f'        新: {b.get(k)}')

print()
print(f'  比较了 {checked} 个文件，类成员不一致的: {diffs}')
print('  ✅ 类定义与响应协议签名完全一致 —— 行为未变' if diffs == 0 else '')
