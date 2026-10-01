# FILE: backend/scripts/audit_document_review.py
"""
V282.34: Audit skanim për services/document_review/.
Identifikon referencat e brendshme, versionet, dhe file-at e padorëzuar.
"""
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent / "app" / "services" / "document_review"

if not ROOT.exists():
    print(f"❌ Nuk gjendet: {ROOT}")
    raise SystemExit(1)

# 1. Mblidh të gjithë file-at .py
py_files = sorted(ROOT.rglob("*.py"))
py_files = [f for f in py_files if "__pycache__" not in str(f)]

print(f"\n{'=' * 70}")
print(f"SKANIM: {ROOT}")
print(f"Total .py files: {len(py_files)}")
print(f"{'=' * 70}")

# 2. Map module_name -> file
mod_map = {}
for f in py_files:
    rel = f.relative_to(ROOT)
    # modul path si "verify.verifier" ose "hallucination.checker"
    mod = str(rel.with_suffix("")).replace("\\", "/").replace("/", ".")
    if mod.endswith(".__init__"):
        mod = mod[:-9]
    mod_map[mod] = f

# 3. Skano imports + VERSION strings
import_re = re.compile(
    r"^\s*(?:from|import)\s+(app\.services\.document_review[\w\.]*)",
    re.MULTILINE,
)
version_re = re.compile(r"V(\d+\.\d+)")

refs = defaultdict(list)   # module -> list of (referrer, line_no, line)
versions = defaultdict(set)

for f in py_files:
    try:
        txt = f.read_text(encoding="utf-8")
    except Exception:
        continue
    rel = str(f.relative_to(ROOT)).replace("\\", "/")

    for m in version_re.finditer(txt):
        versions[rel].add(m.group(1))

    for m in import_re.finditer(txt):
        target = m.group(1)
        refs[target].append((rel, txt[:m.start()].count("\n") + 1))

# 4. Raport: versionet
print("\n📌 VERSIONET (V<nr>) — per file:")
for rel in sorted(versions.keys()):
    vs = sorted(versions[rel])
    print(f"  {rel:55} -> V{', V'.join(vs)}")

# 5. Raport: file-at e padorëzuar (nuk referohen nga askund)
print("\n📌 FILE-A TË PADORËZUAR (nuk importohen nga brenda document_review/):")
for mod, f in sorted(mod_map.items()):
    if mod.endswith("__init__"):
        continue
    full_mod = f"app.services.document_review.{mod}"
    referenced = False
    for target in refs:
        if target == full_mod or target.startswith(full_mod + "."):
            referenced = True
            break
    if not referenced:
        print(f"  ⚠️  {mod:55} ({f.relative_to(ROOT)})")

# 6. Raport: file-a që importojnë mongo_verifier
print("\n📌 FILE-A QË IMPORTON mongo_verifier:")
for f in py_files:
    try:
        txt = f.read_text(encoding="utf-8")
    except Exception:
        continue
    if "mongo_verifier" in txt:
        rel = str(f.relative_to(ROOT)).replace("\\", "/")
        cnt = txt.count("mongo_verifier")
        print(f"  {rel:55} ({cnt} hits)")

# 7. Raport: file-a që importojnë citation_extractor / fact_extractor
print("\n📌 FILE-A QË IMPORTON citation_extractor / fact_extractor:")
for f in py_files:
    try:
        txt = f.read_text(encoding="utf-8")
    except Exception:
        continue
    hits = []
    if "citation_extractor" in txt:
        hits.append("citation_extractor")
    if "fact_extractor" in txt:
        hits.append("fact_extractor")
    if hits:
        rel = str(f.relative_to(ROOT)).replace("\\", "/")
        print(f"  {rel:55} -> {', '.join(hits)}")

print(f"\n{'=' * 70}\n")
