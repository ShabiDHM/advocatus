# FILE: backend/scripts/audit_document_review_external.py
"""
V282.34: Skanim global — kush importon services.document_review.* nga e gjithë app/.
Identifikon file-at e vërtetë të padorëzuar (mbetje).
"""
import re
from pathlib import Path
from collections import defaultdict

BACKEND = Path(__file__).resolve().parent.parent
APP = BACKEND / "app"
DR = APP / "services" / "document_review"

if not DR.exists():
    print(f"❌ Nuk gjendet: {DR}")
    raise SystemExit(1)

# Modulet që ekzistojnë brenda document_review
dr_modules = set()
for f in DR.rglob("*.py"):
    if "__pycache__" in str(f):
        continue
    rel = f.relative_to(DR)
    mod = str(rel.with_suffix("")).replace("\\", "/").replace("/", ".")
    if mod.endswith(".__init__"):
        mod = mod[:-9]
    dr_modules.add(f"app.services.document_review.{mod}")

# Skano të gjithë app/ për importe document_review
import_re = re.compile(
    r"^\s*(?:from|import)\s+(app\.services\.document_review[\w\.]*)",
    re.MULTILINE,
)

# external_uses[module] = list of (referrer, line_no)
external_uses = defaultdict(list)

for f in APP.rglob("*.py"):
    if "__pycache__" in str(f):
        continue
    try:
        txt = f.read_text(encoding="utf-8")
    except Exception:
        continue
    rel = str(f.relative_to(BACKEND)).replace("\\", "/")
    for m in import_re.finditer(txt):
        target = m.group(1)
        line_no = txt[:m.start()].count("\n") + 1
        external_uses[target].append((rel, line_no))

# Raport
print(f"\n{'=' * 78}")
print(f"GLOBAL SCAN: kush importon document_review.* (nga e gjithë app/)")
print(f"{'=' * 78}")

# Group by submodule (pa attribute)
by_module = defaultdict(list)
for target, uses in external_uses.items():
    # Normalizo: përdor modulin më të gjatë që ekziston
    parts = target.split(".")
    matched = None
    for i in range(len(parts), 0, -1):
        candidate = ".".join(parts[:i])
        if candidate in dr_modules or candidate == "app.services.document_review":
            matched = candidate
            break
    if matched:
        for ref, ln in uses:
            # Skip self-imports
            if ref.startswith("app/services/document_review/") and matched != "app.services.document_review":
                pass  # keep, por shëno
            by_module[matched].append((ref, ln, target))

print("\n📌 MODULET E KONSUMUARA NGA JASHTË:")
for mod in sorted(by_module.keys()):
    ext_uses = [u for u in by_module[mod]
                if not u[0].startswith("app/services/document_review/")]
    int_uses = [u for u in by_module[mod]
                if u[0].startswith("app/services/document_review/")]
    print(f"\n  ▶ {mod}")
    if ext_uses:
        print(f"    EXTERNAL ({len(ext_uses)}):")
        for ref, ln, target in ext_uses[:15]:
            print(f"      {ref}:{ln}  -> {target}")
    else:
        print(f"    ⚠️  NUK importohet nga jashtë!")
    if int_uses:
        print(f"    (internal: {len(int_uses)} hits)")

# Cilat file-a janë totalisht të padorëzuar (as jashtë, as brenda)
print(f"\n{'=' * 78}")
print("📌 FILE-A TOTALISHT TË PADORËZUAR (mbetje të vërteta):")
print(f"{'=' * 78}\n")

all_mods_used = set(external_uses.keys())
# Përfshi edhe ato që përdoren brenda document_review
internal_imports = set()
for f in DR.rglob("*.py"):
    if "__pycache__" in str(f):
        continue
    try:
        txt = f.read_text(encoding="utf-8")
    except Exception:
        continue
    for m in import_re.finditer(txt):
        internal_imports.add(m.group(1))

used_set = all_mods_used | internal_imports

orphans = []
for mod in sorted(dr_modules):
    used = False
    for u in used_set:
        if u == mod or u.startswith(mod + "."):
            used = True
            break
    if not used and not mod.endswith("__init__"):
        orphans.append(mod)

if orphans:
    for o in orphans:
        print(f"  🗑️  {o}")
else:
    print("  (asnjë)")

print(f"\n{'=' * 78}\n")