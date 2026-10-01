# FILE: backend/scripts/remove_dead_typing_imports.py
"""
Heq dead imports NGA `typing` (vetëm moduli typing).

- Dry-run: --dry-run për të parë ndryshimet pa i aplikuar.
- Verifikon me re-parse para se të ruajë.
- Ruan komente në rresht (suffix).
- Nuk prek __init__.py, _deprecated/, __pycache__/.
"""

import ast
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

TYPO_PATTERN = re.compile(
    r'^(\s*from\s+typing\s+import\s+)(.+?)(\s*(?:#.*)?)$'
)


def _collect_used_names(tree: ast.AST) -> Set[str]:
    used: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            cur = node
            while isinstance(cur, ast.Attribute):
                cur = cur.value
            if isinstance(cur, ast.Name):
                used.add(cur.id)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            for tok in re.findall(r'\b\w+\b', node.value):
                used.add(tok)
    return used


def _find_dead_typing_imports(source: str) -> Dict[int, Set[str]]:
    """Kthen {lineno: {emri_i_vdekur, ...}} për `from typing import ...`."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}

    used = _collect_used_names(tree)
    result: Dict[int, Set[str]] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "typing":
            for alias in node.names:
                local = alias.asname or alias.name
                if local not in used:
                    result.setdefault(node.lineno, set()).add(local)

    return result


def _remove_names_from_line(line: str, names: Set[str]) -> str:
    m = TYPO_PATTERN.match(line)
    if not m:
        return line

    prefix, imports_str, suffix = m.group(1), m.group(2), m.group(3) or ''

    parts = [p.strip() for p in imports_str.split(',')]
    kept: List[str] = []
    for p in parts:
        base = p.split(' as ')[0].strip()
        if base not in names:
            kept.append(p)

    if not kept:
        return ''  # rreshti bëhet bosh (Python e toleron)

    return f"{prefix}{', '.join(kept)}{suffix}"


def process_file(path: Path, dry_run: bool) -> Tuple[int, bool]:
    try:
        source = path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"  ⚠️  {path.name}: nuk lexohet — {e}")
        return 0, False

    dead = _find_dead_typing_imports(source)
    if not dead:
        return 0, True

    lines = source.split('\n')
    for lineno, names in dead.items():
        idx = lineno - 1
        if 0 <= idx < len(lines):
            lines[idx] = _remove_names_from_line(lines[idx], names)

    new_source = '\n'.join(lines)

    try:
        ast.parse(new_source)
    except SyntaxError as e:
        print(f"  ❌ {path.name}: syntax error pas editimit — {e}")
        return 0, False

    n = sum(len(s) for s in dead.values())

    if dry_run:
        print(f"  [DRY] {path}: {n} dead typing import(s)")
        for lineno, names in sorted(dead.items()):
            print(f"        L{lineno}: {sorted(names)}")
    else:
        path.write_text(new_source, encoding='utf-8')
        print(f"  ✅ {path}: {n} u hoqën")

    return n, True


def main():
    dry_run = '--dry-run' in sys.argv

    backend = Path(__file__).resolve().parent.parent
    app = backend / 'app'
    if not app.exists():
        print(f"❌ Nuk u gjet: {app}")
        sys.exit(1)

    files = sorted(
        p for p in app.rglob('*.py')
        if p.name != '__init__.py'
        and '_deprecated' not in p.parts
        and '__pycache__' not in p.parts
    )

    mode = "DRY-RUN" if dry_run else "APLIKIM"
    print("=" * 70)
    print(f"REMOVE DEAD TYPING IMPORTS — {mode}")
    print("=" * 70)

    total = 0
    changed_files = 0
    failed = 0

    for f in files:
        n, ok = process_file(f, dry_run)
        if not ok:
            failed += 1
        elif n > 0:
            total += n
            changed_files += 1

    print("\n" + "=" * 70)
    print(f"  Importe të hequra:  {total}")
    print(f"  File-a të prekura:   {changed_files}")
    print(f"  Dështime:            {failed}")
    print("=" * 70)
    if dry_run:
        print("\nℹ️  DRY-RUN — asnjë file nuk u modifikua.")
        print("    Për aplikim: python scripts\\remove_dead_typing_imports.py")


if __name__ == '__main__':
    main()