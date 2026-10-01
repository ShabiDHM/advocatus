# FILE: backend/scripts/audit_orphan_modules.py
"""
V282.36: Audit precize për 4 module që skanimi global i raportoi si orphan.
Kontrollon:
  1. Importe reale (jo vetëm substring).
  2. Referenca në f-string, komente, docstring.
  3. Referenca në tests/, scripts/.
  4. Referenca në __init__.py (re-export).
"""
import re
from pathlib import Path
from collections import defaultdict

BACKEND = Path(__file__).resolve().parent.parent
APP = BACKEND / "app"
SCRIPTS = BACKEND / "scripts"
TESTS = BACKEND / "tests"

ORPHANS = [
    "analytics_service",
    "defendant_group_extractor",
    "social_service",
    "text_sterilization_service",
]

# Fushat për skanim
ROOTS = [APP, SCRIPTS]
if TESTS.exists():
    ROOTS.append(TESTS)

# Heuristic patterns
IMPORT_RE = re.compile(
    r'^\s*(?:from\s+[\w\.]*?\b{name}\b|import\s+[\w\.]*?\b{name}\b)',
    re.MULTILINE,
)
FULL_IMPORT_RE = re.compile(
    r'from\s+app\.services\.{name}\s+import|from\s+\.{name}\s+import|import\s+app\.services\.{name}',
    re.MULTILINE,
)
NAME_RE = re.compile(r'\b{name}\b')

# Folders që injorohen
SKIP_PARTS = {"__pycache__", ".venv", "venv", "node_modules", ".git"}


def _should_skip(path: Path) -> bool:
    return any(p in SKIP_PARTS for p in path.parts)


def scan_module(name: str) -> dict:
    """Kthen detajet e përdorimit për një modul."""
    results = {
        "imports": [],       # Importe reale (në fillim të rreshtit)
        "full_imports": [],  # Importe absolute relative
        "substring": [],     # Referenca të tjera (komente, f-string, etj.)
    }

    # Fusha e skanimit
    for root in ROOTS:
        if not root.exists():
            continue
        for f in root.rglob("*.py"):
            if _should_skip(f):
                continue
            if f.name == f"{name}.py":
                continue  # skip veten
            try:
                txt = f.read_text(encoding="utf-8")
            except Exception:
                continue

            rel = str(f.relative_to(BACKEND)).replace("\\", "/")

            # 1. Full imports
            for m in re.finditer(
                rf'from\s+(?:app\.services\.|\.){re.escape(name)}\s+import|'
                rf'import\s+app\.services\.{re.escape(name)}',
                txt,
            ):
                ln = txt[:m.start()].count("\n") + 1
                results["full_imports"].append((rel, ln, m.group(0)))

            # 2. Line-start imports
            for m in IMPORT_RE.finditer(txt):
                ln = txt[:m.start()].count("\n") + 1
                results["imports"].append((rel, ln, m.group(0).strip()))

            # 3. Substring matches (jo import)
            for m in NAME_RE.finditer(txt):
                ln = txt[:m.start()].count("\n") + 1
                line = txt.split("\n")[ln - 1].strip()[:120]
                results["substring"].append((rel, ln, line))

    return results


print(f"\n{'=' * 78}")
print("AUDIT PRECIZE — ORPHAN MODULES")
print(f"{'=' * 78}")

for name in ORPHANS:
    print(f"\n{'─' * 78}")
    print(f"▶ {name}.py")
    print(f"{'─' * 78}")

    r = scan_module(name)

    if r["full_imports"]:
        print(f"  🟢 FULL IMPORTS ({len(r['full_imports'])}):")
        for rel, ln, snippet in r["full_imports"][:10]:
            print(f"      {rel}:{ln}  → {snippet[:80]}")
    else:
        print(f"  🔴 FULL IMPORTS: (asnjë)")

    if r["imports"]:
        print(f"  🟡 LINE-START IMPORTS ({len(r['imports'])}):")
        for rel, ln, snippet in r["imports"][:5]:
            print(f"      {rel}:{ln}  → {snippet[:80]}")

    if r["substring"]:
        # Filtro referencat brenda vetë moduleve services/ (mund të jenë vetëm references në komente)
        external = [
            (rel, ln, line) for rel, ln, line in r["substring"]
            if not rel.startswith(f"app/services/{name}")
        ]
        if external:
            print(f"  🟡 SUBSTRING REFERENCES ({len(external)}):")
            for rel, ln, line in external[:8]:
                print(f"      {rel}:{ln}  → {line[:80]}")
        else:
            print(f"  ✅ SUBSTRING: vetëm brenda modulit (komente/docstring)")

    print()

print(f"{'=' * 78}\n")