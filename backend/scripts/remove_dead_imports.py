# FILE: backend/scripts/remove_dead_imports.py
"""
Heq dead imports jo-typing në app/.

- --dry-run     : vetëm raporton, nuk modifikon.
- --internal    : përfshin edhe importet app.* (default: skip).
                  Me këtë flag, kontrollon re-export para heqjes.

KONSERVATORE: Heq VETËM importe që i përkasin STDLIB ose THIRDPARTY
të listuara eksplicit. Gjithçka tjetër (përfshirë module relative
si `patterns`, `helpers`, `normalize`) trajtohet si internal dhe
kërkon --internal.
"""

import ast
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


STDLIB = {
    "json", "os", "re", "sys", "time", "shutil", "urllib",
    "base64", "tempfile", "mimetypes", "zipfile", "hashlib",
    "datetime", "pathlib", "subprocess", "logging", "asyncio",
    "typing", "collections", "itertools", "functools", "io",
    "math", "random", "string", "copy", "enum", "dataclasses",
    "uuid", "secrets", "csv", "sqlite3", "threading", "queue",
}

THIRDPARTY = {
    "fastapi", "jose", "bson", "redis", "botocore",
    "reportlab", "langdetect", "pydantic", "httpx",
    "requests", "aiohttp", "pymongo", "celery", "openai",
    "dotenv", "PIL", "pandas", "numpy", "passlib", "jwt",
    "starlette", "uvicorn", "motor", "boto3",
}

IMPORT_LINE = re.compile(
    r'^(\s*)(?:'
    r'(import\s+)(.+?)(\s*(?:#.*)?)$'
    r'|'
    r'(from\s+)([\w\.]+)(\s+import\s+)(.+?)(\s*(?:#.*)?)$'
    r')'
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


def _module_path_for_file(path: Path, app_root: Path) -> str:
    """Kthen 'app.services.llm.llm_client' për file në app/services/llm/llm_client.py."""
    rel = path.relative_to(app_root.parent).with_suffix('')
    parts = list(rel.parts)
    if parts and parts[-1] == '__init__':
        parts = parts[:-1]
    return '.'.join(parts)


def _find_dead_imports(
    source: str
) -> List[Tuple[int, str, str, str]]:
    """
    Kthen listë me (lineno, kind, module_or_empty, name).
    kind: 'import' ose 'from'.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    used = _collect_used_names(tree)
    dead: List[Tuple[int, str, str, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split('.')[0]
                if local.startswith('_'):
                    continue
                if local not in used:
                    dead.append((node.lineno, 'import', '', alias.name))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ''
            for alias in node.names:
                if alias.name == '*':
                    continue
                if alias.name == 'annotations':
                    continue
                local = alias.asname or alias.name
                if local.startswith('_'):
                    continue
                if local in used:
                    continue
                dead.append((node.lineno, 'from', mod, alias.name))

    return dead


def _is_reexported(
    name: str,
    module_path: str,
    all_sources: Dict[Path, str],
    exclude: Path
) -> bool:
    """Kontrollo nëse `name` importohet nga `module_path` në ndonjë file tjetër."""
    pattern = re.compile(
        r'from\s+' + re.escape(module_path) + r'\s+import\s+([^\n#]+)'
    )
    for path, src in all_sources.items():
        if path == exclude:
            continue
        for m in pattern.finditer(src):
            names = [n.strip().split(' as ')[0] for n in m.group(1).split(',')]
            if name in names:
                return True
    return False


def _should_skip_by_category(module: str, include_internal: bool) -> bool:
    """
    Konservatore: heq VETËM nëse moduli është eksplicit në STDLIB ose THIRDPARTY.
    Gjithçka tjetër → trajtohet si internal (skip pa --internal).
    """
    top = module.split('.')[0] if module else ''
    if top in STDLIB or top in THIRDPARTY:
        return False  # i sigurt për heqje
    return not include_internal  # internal → skip pa --internal


def _rewrite_line_import(
    line: str, names_to_remove: Set[str]
) -> str:
    m = IMPORT_LINE.match(line)
    if not m:
        return line

    indent = m.group(1)
    if m.group(2):  # import X, Y
        prefix = m.group(2)
        items = [x.strip() for x in m.group(3).split(',')]
        suffix = m.group(4) or ''
        kept = [i for i in items
                if (i.split(' as ')[-1].strip() not in names_to_remove
                    and i.split('.')[0].strip() not in names_to_remove)]
        if not kept:
            return ''
        return f"{indent}{prefix}{', '.join(kept)}{suffix}"

    # from M import ...
    from_w = m.group(5)
    module = m.group(6)
    import_w = m.group(7)
    items = [x.strip() for x in m.group(8).split(',')]
    suffix = m.group(9) or ''
    kept = [i for i in items
            if (i.split(' as ')[-1].strip() not in names_to_remove
                and i.split(' as ')[0].strip() not in names_to_remove)]
    if not kept:
        return ''
    return f"{indent}{from_w}{module}{import_w}{', '.join(kept)}{suffix}"


def process_file(
    path: Path,
    app_root: Path,
    all_sources: Dict[Path, str],
    include_internal: bool,
    dry_run: bool,
) -> Tuple[int, bool]:
    source = all_sources[path]
    dead = _find_dead_imports(source)
    if not dead:
        return 0, True

    module_path = _module_path_for_file(path, app_root)

    to_remove: Dict[int, Set[str]] = {}
    skipped_reexport = 0

    for lineno, kind, module, name in dead:
        if kind == 'from':
            if _should_skip_by_category(module, include_internal):
                continue
            if module.startswith('app') or module.startswith('app.'):
                if _is_reexported(name, module_path, all_sources, path):
                    skipped_reexport += 1
                    continue
        else:  # import X
            top = name.split('.')[0]
            if top in STDLIB or top in THIRDPARTY:
                pass  # OK
            elif top.startswith('app'):
                if not include_internal:
                    continue
            else:
                # unknown module → konservatore: skip pa --internal
                if not include_internal:
                    continue
        to_remove.setdefault(lineno, set()).add(name)

    if not to_remove:
        if skipped_reexport > 0:
            print(f"  [SKIP] {path.relative_to(app_root)}: "
                  f"{skipped_reexport} re-export u ruajtën")
        return 0, True

    lines = source.split('\n')
    for lineno, names in to_remove.items():
        idx = lineno - 1
        if 0 <= idx < len(lines):
            lines[idx] = _rewrite_line_import(lines[idx], names)

    new_source = '\n'.join(lines)

    try:
        ast.parse(new_source)
    except SyntaxError as e:
        print(f"  [FAIL] {path.relative_to(app_root)}: syntax error pas editimit - {e}")
        return 0, False

    n = sum(len(s) for s in to_remove.values())

    if dry_run:
        print(f"  [DRY] {path.relative_to(app_root)}: {n} dead")
        for lineno, names in sorted(to_remove.items()):
            print(f"        L{lineno}: {sorted(names)}")
    else:
        path.write_text(new_source, encoding='utf-8')
        print(f"  [OK] {path.relative_to(app_root)}: {n} u hoqen "
              f"(skip {skipped_reexport} re-export)")

    return n, True


def main():
    dry_run = '--dry-run' in sys.argv
    include_internal = '--internal' in sys.argv

    backend = Path(__file__).resolve().parent.parent
    app = backend / 'app'
    if not app.exists():
        print(f"Nuk u gjet: {app}")
        sys.exit(1)

    files = sorted(
        p for p in app.rglob('*.py')
        if p.name != '__init__.py'
        and '_deprecated' not in p.parts
        and '__pycache__' not in p.parts
    )

    all_sources: Dict[Path, str] = {}
    for f in files:
        try:
            all_sources[f] = f.read_text(encoding='utf-8')
        except Exception:
            pass

    mode = "DRY-RUN" if dry_run else "APLIKIM"
    internal = "ME app.*" if include_internal else "VETEM stdlib+third-party"
    print("=" * 74)
    print(f"REMOVE DEAD IMPORTS (jo-typing) - {mode} - {internal}")
    print("=" * 74)

    total = 0
    changed = 0
    failed = 0

    for f in files:
        if f not in all_sources:
            continue
        n, ok = process_file(f, app, all_sources, include_internal, dry_run)
        if not ok:
            failed += 1
        elif n > 0:
            total += n
            changed += 1

    print("\n" + "=" * 74)
    print(f"  Importe te hequra:  {total}")
    print(f"  File-a te prekura:   {changed}")
    print(f"  Deshtime:            {failed}")
    print("=" * 74)
    if dry_run:
        print("\nDRY-RUN - asnje file nuk u modifikua.")
        print("    Aplikim i sigurt (pa app.*):")
        print("      python scripts\\remove_dead_imports.py")
        print("    Perfshire app.* (me re-export check):")
        print("      python scripts\\remove_dead_imports.py --internal")


if __name__ == '__main__':
    main()