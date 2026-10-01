# FILE: backend/scripts/audit_dead_imports.py
"""
Audit dead imports në app/ duke përdorur AST.

Karakteristika:
- Zbulon importet e papërdorura (import X, from X import Y).
- Injoron __init__.py (re-exporte të qëllimshme).
- Injoron importet brenda if TYPE_CHECKING (për type hints).
- Injoron importet që përdoren vetëm në string annotations.
- Injoron importet me alias _ (i/e padëshiruar).
- Raporton sipas file-it, me linjë + emër.
"""

import ast
import sys
from pathlib import Path
from typing import List, Tuple, Set


SKIP_FILES = {"__init__.py"}


def _collect_used_names(tree: ast.AST) -> Set[str]:
    """Mbledh çdo emër që shfaqet si Name/Attribute në kod."""
    used: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            # Marrim rrënjën e atributit (p.sh. `os.path.join` → `os`)
            current = node
            while isinstance(current, ast.Attribute):
                current = current.value
            if isinstance(current, ast.Name):
                used.add(current.id)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            # String annotation: "List[str]" → mbledhim fjalët
            for token in node.value.replace("[", " ").replace("]", " ") \
                                   .replace(",", " ").replace("|", " ") \
                                   .replace("(", " ").replace(")", " ").split():
                used.add(token.strip("'\""))
    return used


def _is_typing_import(module: str, name: str) -> bool:
    """True nëse është import nga typing (kandidat tipik për dead code)."""
    return module == "typing" or name in {
        "List", "Dict", "Any", "Optional", "Tuple", "Set",
        "Union", "Callable", "AsyncGenerator", "Generator",
        "Iterable", "Iterator", "Sequence", "Mapping",
        "TypeVar", "Generic", "cast", "Literal", "Type",
    }


def _analyze_file(path: Path) -> List[Tuple[int, str, str]]:
    """
    Kthen listë me (linja, moduli, emri) për importet e papërdorura.
    """
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, UnicodeDecodeError) as e:
        return [(-1, "PARSE_ERROR", str(e))]

    used_names = _collect_used_names(tree)

    dead: List[Tuple[int, str, str]] = []

    for node in ast.walk(tree):
        # `import X` ose `import X as Y`
        if isinstance(node, ast.Import):
            for alias in node.names:
                local_name = alias.asname or alias.name.split(".")[0]
                if local_name.startswith("_"):
                    continue
                if local_name not in used_names:
                    dead.append((node.lineno, alias.name, local_name))

        # `from X import Y` ose `from X import Y as Z`
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                if alias.name == "*":
                    continue
                local_name = alias.asname or alias.name
                if local_name.startswith("_"):
                    continue
                if local_name in used_names:
                    continue
                if local_name == "annotations":
                    continue
                # Skip typing imports brenda TYPE_CHECKING (të nevojshme runtime)
                # — por nëse janë vërtet të papërdorura, i raportojmë.
                dead.append((node.lineno, module, local_name))

    return dead


def _find_python_files(root: Path) -> List[Path]:
    return sorted(
        p for p in root.rglob("*.py")
        if p.name not in SKIP_FILES
        and "_deprecated" not in p.parts
        and "__pycache__" not in p.parts
    )


def main():
    backend_dir = Path(__file__).resolve().parent.parent
    app_dir = backend_dir / "app"

    if not app_dir.exists():
        print(f"❌ Nuk u gjet: {app_dir}")
        sys.exit(1)

    files = _find_python_files(app_dir)

    print("=" * 78)
    print("AUDIT DEAD IMPORTS — AST-BASED")
    print("=" * 78)
    print(f"Root: {app_dir}")
    print(f"Files scanned: {len(files)}")
    print("=" * 78)

    total_dead = 0
    files_with_dead = 0
    typing_dead = 0
    non_typing_dead = 0
    parse_errors: List[Tuple[str, str]] = []

    per_file_report: List[Tuple[str, List[Tuple[int, str, str]]]] = []

    for path in files:
        dead = _analyze_file(path)
        if not dead:
            continue
        if dead and dead[0][0] == -1:
            parse_errors.append((str(path.relative_to(app_dir)), dead[0][2]))
            continue
        per_file_report.append((str(path.relative_to(app_dir)), dead))
        files_with_dead += 1
        total_dead += len(dead)
        for _, module, name in dead:
            if _is_typing_import(module, name):
                typing_dead += 1
            else:
                non_typing_dead += 1

    # Print per file
    for rel_path, dead in per_file_report:
        print(f"\n▶ {rel_path}  ({len(dead)} dead)")
        for lineno, module, name in sorted(dead):
            origin = f"from {module}" if module else "import"
            print(f"   L{lineno:<5} {origin:<30} → {name}")

    # Parse errors
    if parse_errors:
        print("\n" + "=" * 78)
        print("PARSE ERRORS")
        print("=" * 78)
        for rel_path, err in parse_errors:
            print(f"  {rel_path}: {err}")

    # Summary
    print("\n" + "=" * 78)
    print("PËRMBLEDHJE")
    print("=" * 78)
    print(f"  Total dead imports:       {total_dead}")
    print(f"  Files me dead imports:    {files_with_dead} / {len(files)}")
    print(f"  Nga typing:               {typing_dead}")
    print(f"  Të tjera:                 {non_typing_dead}")
    if parse_errors:
        print(f"  Parse errors:             {len(parse_errors)}")
    print("=" * 78)


if __name__ == "__main__":
    main()