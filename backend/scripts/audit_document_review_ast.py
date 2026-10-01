# FILE: backend/scripts/audit_document_review_ast.py
"""
V282.34: AST-based audit për services/document_review/.
Kap importet absolute + relative + importlib.import_module.
"""
import ast
import re
from pathlib import Path
from collections import defaultdict

BACKEND = Path(__file__).resolve().parent.parent
APP = BACKEND / "app"
DR = APP / "services" / "document_review"


def module_name_from_path(py_file: Path, root: Path) -> str:
    """app.services.document_review.verify.verifier from file path."""
    rel = py_file.relative_to(BACKEND).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def resolve_relative(module: str, level: int, current_module: str) -> str:
    """
    Resolve relative import.
    current_module: 'app.services.document_review.verify.verifier'
    level: number of dots (1 = '.', 2 = '..')
    module: '.verifier' or 'verifier' etc (already stripped)
    """
    if level == 0:
        return module
    # current_package = current_module minus last component (if not __init__)
    # Actually, for relative imports, the package is where the file lives
    # Simplify: current file's module = current_module; for level N, go up N-1
    parts = current_module.split(".")
    # level=1: same package (parent of file's module if it's a module)
    # Hmm - actually in Python, `from . import X` in module `a.b.c` imports from package `a.b`
    # where c is a module (not __init__).
    # So we need to know if current_module is a package (file is __init__.py)
    # For simplicity: assume level=1 means up 1 from full module path
    base = parts[:-level] if level <= len(parts) else []
    if module:
        return ".".join(base + module.split("."))
    return ".".join(base)


def get_imports(py_file: Path) -> list:
    """Kthen listë me module target absolute që importohen."""
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
    except Exception:
        return []

    current_mod = module_name_from_path(py_file, BACKEND)
    targets = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                targets.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                # relative
                if node.module:
                    resolved = resolve_relative(node.module, node.level, current_mod)
                    targets.append(resolved)
                    # Also include submodule path as candidate
                    for alias in node.names:
                        targets.append(f"{resolved}.{alias.name}")
                else:
                    # `from . import X` -> X as submodule of base
                    base = resolve_relative("", node.level, current_mod)
                    for alias in node.names:
                        targets.append(f"{base}.{alias.name}")
            else:
                if node.module:
                    targets.append(node.module)
                    for alias in node.names:
                        targets.append(f"{node.module}.{alias.name}")

    return targets


def get_dynamic_imports(py_file: Path) -> list:
    """importlib.import_module('x.y') ose __import__('x.y') si string."""
    try:
        txt = py_file.read_text(encoding="utf-8")
    except Exception:
        return []

    targets = []
    pat = re.compile(
        r"""(?:importlib\.import_module|__import__)\s*\(\s*['"]([\w\.]+)['"]"""
    )
    for m in pat.finditer(txt):
        targets.append(m.group(1))
    return targets


# 1. Mblidh dr_modules
dr_modules = set()
for f in DR.rglob("*.py"):
    if "__pycache__" in str(f):
        continue
    dr_modules.add(module_name_from_path(f, BACKEND))

# 2. Skano të gjithë app/ për imports
all_py = [f for f in APP.rglob("*.py") if "__pycache__" not in str(f)]
external_uses = defaultdict(list)  # target -> [(referrer_rel, line?)]
internal_uses = defaultdict(list)

for f in all_py:
    rel = str(f.relative_to(BACKEND)).replace("\\", "/")
    is_dr = rel.startswith("app/services/document_review/")
    targets = get_imports(f) + get_dynamic_imports(f)

    for t in targets:
        # Match kundrejt dr_modules (duke përfshirë submodule chains)
        matched = None
        for dr_m in dr_modules:
            if t == dr_m or t.startswith(dr_m + "."):
                # preferojmë më të gjatë
                if matched is None or len(dr_m) > len(matched):
                    matched = dr_m
        if matched:
            if is_dr and not rel.endswith("__init__.py"):
                # Self/internal — kontrollo a është vetë file-i
                if matched != module_name_from_path(f, BACKEND):
                    internal_uses[matched].append(rel)
            else:
                internal_uses[matched].append(rel)

# 3. Actually, we want external vs internal distinction:
external_uses = defaultdict(list)
internal_uses = defaultdict(list)

for f in all_py:
    rel = str(f.relative_to(BACKEND)).replace("\\", "/")
    is_dr = rel.startswith("app/services/document_review/")
    this_mod = module_name_from_path(f, BACKEND) if is_dr else None

    targets = get_imports(f) + get_dynamic_imports(f)

    for t in targets:
        matched = None
        for dr_m in dr_modules:
            if t == dr_m or t.startswith(dr_m + "."):
                if matched is None or len(dr_m) > len(matched):
                    matched = dr_m
        if not matched:
            continue
        # Self-import skip
        if this_mod and matched == this_mod:
            continue
        if is_dr:
            internal_uses[matched].append(rel)
        else:
            external_uses[matched].append(rel)

# 4. Raport
print(f"\n{'=' * 78}")
print("AST AUDIT — services/document_review/")
print(f"{'=' * 78}")
print(f"DR modules found: {len(dr_modules)}")

print(f"\n📌 EXTERNAL CONSUMERS (nga jashtë document_review/):")
all_used = set()
for mod in sorted(external_uses.keys()):
    refs = sorted(set(external_uses[mod]))
    all_used.add(mod)
    print(f"  ▶ {mod}")
    for r in refs:
        print(f"      ← {r}")

print(f"\n📌 INTERNAL ONLY (përdorur vetëm brenda document_review/):")
for mod in sorted(internal_uses.keys()):
    if mod in external_uses:
        continue
    refs = sorted(set(internal_uses[mod]))
    print(f"  ▶ {mod}  ({len(refs)} internal refs)")

print(f"\n📌 TË PADORËZUAR (as external, as internal):")
# Konsidero "used" edhe ato ku një modul X përdoret nga Y, dhe Y përdoret nga Z... transitively
# Për thjeshtësi: nëse një modul ka __init__ që e re-export, mbaj.
orphans = []
for mod in sorted(dr_modules):
    if mod.endswith("__main__"):
        continue
    if mod in external_uses or mod in internal_uses:
        continue
    # Kontrollo a ka __init__.py që e eksporton
    orphans.append(mod)

for o in orphans:
    print(f"  🗑️  {o}")

print(f"\n{'=' * 78}\n")