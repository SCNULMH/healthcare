from __future__ import annotations

import ast
import sys
from pathlib import Path


def map_python(path: Path) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    lines: list[str] = [f"# RepoMap: {path.as_posix()}"]
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            lines.append(f"class {node.name}: line {node.lineno}")
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    prefix = "async def" if isinstance(child, ast.AsyncFunctionDef) else "def"
                    lines.append(f"  {prefix} {child.name}: line {child.lineno}")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            lines.append(f"{prefix} {node.name}: line {node.lineno}")
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python scripts/repo_map.py <python-file>")
        return 2
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"missing file: {path}")
        return 2
    if path.suffix != ".py":
        print(f"RepoMap only supports Python for now: {path}")
        return 2
    print(map_python(path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
