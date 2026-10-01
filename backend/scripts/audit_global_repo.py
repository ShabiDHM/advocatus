# FILE: backend/scripts/audit_global_repo.py
"""
V282.36: Skanim global repo-wide.
Kontrollon:
  1. Referencat AI të vjetra (Claude, ChatGPT, GPT-4, Anthropic, OpenAI).
  2. Çmimet (19.99 / 49.99 / 99.99).
  3. Routes (/api/v1/ vs /api/).
  4. Emri i vjetër "org_id" vs "organization_id".
  5. Emri hardcoded "Shaban Bala".
  6. Dead imports në Python files.
"""
import re
from pathlib import Path
from collections import defaultdict

BACKEND = Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent  # advocatus/
APP = BACKEND / "app"
FRONTEND_SRC = ROOT / "frontend" / "src"

# ═══════════════════════════════════════════════════════════════════════════
# Pattern-et për skanim
# ═══════════════════════════════════════════════════════════════════════════

PATTERNS = {
    "AI_REFERENCES": re.compile(
        r'\b(Claude|Anthropic|ChatGPT|GPT-4|GPT-4o|OpenAI)\b',
        re.IGNORECASE,
    ),
    "PRICING": re.compile(
        r'\b(19\.99|49\.99|99\.99|9\.99|29\.99)\b',
    ),
    "API_ROUTES": re.compile(
        r'["\']/api/v1|["\']/api/(?!v\d)',
    ),
    "ORG_ID_LEGACY": re.compile(
        r'\borg_id\b',
    ),
    "HARDCODED_NAME": re.compile(
        r'\bShaban\s+Bala\b',
        re.IGNORECASE,
    ),
    "REASONING_LEAK": re.compile(
        r'"reasoning":\s*\{\s*"enabled"',
    ),
}

# Extensions që skanohen
EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".md", ".txt", ".yaml", ".yml"}

# Folders që injorohen
SKIP_PARTS = {
    "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
    ".git", ".next", ".cache", "coverage", ".file_cache", ".vscode",
}


def _should_skip(path: Path) -> bool:
    return any(p in SKIP_PARTS for p in path.parts)


def _scan_pattern(name: str, pattern: re.Pattern, roots: list) -> dict:
    hits_by_file = defaultdict(list)
    for root in roots:
        if not root.exists():
            continue
        for f in root.rglob("*"):
            if not f.is_file() or _should_skip(f):
                continue
            if f.suffix.lower() not in EXTS:
                continue
            try:
                txt = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for m in pattern.finditer(txt):
                line_no = txt[:m.start()].count("\n") + 1
                line_txt = txt.split("\n")[line_no - 1].strip()[:120]
                hits_by_file[str(f.relative_to(ROOT))].append(
                    (line_no, line_txt)
                )
    return dict(hits_by_file)


def _print_section(title: str, hits: dict, max_per_file: int = 5):
    print(f"\n{'=' * 78}")
    print(f"▶ {title}")
    print(f"{'=' * 78}")
    if not hits:
        print("  ✅ Zero hits")
        return
    total = sum(len(v) for v in hits.values())
    print(f"  🔴 {total} hits në {len(hits)} file-a\n")
    for fpath in sorted(hits.keys()):
        entries = hits[fpath]
        print(f"  ▶ {fpath}  ({len(entries)} hits)")
        for ln, txt in entries[:max_per_file]:
            print(f"      L{ln}: {txt}")
        if len(entries) > max_per_file:
            print(f"      ... dhe {len(entries) - max_per_file} të tjera")


# ═══════════════════════════════════════════════════════════════════════════
# 1-4: Repo-wide scans
# ═══════════════════════════════════════════════════════════════════════════

roots = [APP, FRONTEND_SRC]

for name, pattern in PATTERNS.items():
    hits = _scan_pattern(name, pattern, roots)
    _print_section(name, hits)


# ═══════════════════════════════════════════════════════════════════════════
# 5: Dead imports (Python)
# ═══════════════════════════════════════════════════════════════════════════

def _detect_dead_imports() -> dict:
    """
    Për çdo file .py, detekton importet ku emri nuk përdoret askund në file.
    Vetëm importet top-level me emër të vetëm (jo wildcard, jo 'as').
    """
    import ast
    results = defaultdict(list)

    for f in APP.rglob("*.py"):
        if _should_skip(f):
            continue
        try:
            src = f.read_text(encoding="utf-8")
            tree = ast.parse(src)
        except Exception:
            continue

        imported_names = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    name = alias.asname or alias.name.split(".")[0]
                    imported_names.append((name, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    name = alias.asname or alias.name
                    imported_names.append((name, node.lineno))

        # Për secilin emër, kontrollo nëse përdoret jashtë import linjës
        for name, lineno in imported_names:
            # Krijo regex për përdorim të emrit
            usage = re.compile(rf'\b{re.escape(name)}\b')
            # Hiq linjat e importeve nga skanimi
            lines = src.split("\n")
            used = False
            for i, line in enumerate(lines):
                if i + 1 == lineno:
                    continue
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                if usage.search(line):
                    used = True
                    break
            if not used:
                results[str(f.relative_to(ROOT))].append((lineno, name))

    return dict(results)


dead = _detect_dead_imports()
_print_section("DEAD IMPORTS (Python)", dead, max_per_file=10)


# ═══════════════════════════════════════════════════════════════════════════
# 6: Orphan Python files (0 hits për emrin e modulit në app/)
# ═══════════════════════════════════════════════════════════════════════════

def _detect_orphan_modules() -> list:
    """Modulet .py brenda app/ që nuk referohen askund në app/."""
    all_py = [f for f in APP.rglob("*.py") if not _should_skip(f)]
    module_names = {}
    for f in all_py:
        rel = f.relative_to(APP).with_suffix("")
        parts = list(rel.parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        modname = ".".join(parts)
        module_names[f] = modname

    # Për secilin modul, kontrollo a përmendet emri i tij në ndonjë file tjetër
    # (jo në veten e tij)
    orphans = []
    for f, modname in module_names.items():
        if f.name == "__init__.py":
            continue
        # Krijo pattern për importin e modulit
        short = modname.split(".")[-1]
        pattern = re.compile(rf'\b{re.escape(short)}\b')

        used = False
        for f2 in all_py:
            if f2 == f:
                continue
            try:
                txt = f2.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if pattern.search(txt):
                used = True
                break
        if not used:
            orphans.append(str(f.relative_to(ROOT)))

    return orphans


print(f"\n{'=' * 78}")
print("▶ ORPHAN PYTHON MODULES (0 referenca në app/)")
print(f"{'=' * 78}")
orphans = _detect_orphan_modules()
if not orphans:
    print("  ✅ Zero orphans")
else:
    for o in sorted(orphans):
        print(f"  🗑️  {o}")