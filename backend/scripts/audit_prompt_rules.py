# FILE: backend/scripts/audit_prompt_rules.py
"""
V282.34: Audit i përdorimit të rule në prompt_sections.py.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 1. Të gjitha rule-t e deklaruara në prompt_rules.py
from app.services.document_review.verify import prompt_rules as PR

declared = set(PR.__all__)
print(f"\n📌 Rule të deklaruara në prompt_rules.py: {len(declared)}")
for r in sorted(declared):
    print(f"   • {r}")

# 2. Të gjitha rule-t që përmenden në prompt_sections.py
sections_src = (Path(__file__).resolve().parent.parent /
                "app/services/document_review/verify/prompt_sections.py").read_text(encoding="utf-8")

used = set()
for r in declared:
    # Kontrollo nëse rule shfaqet si identifikues në source (import ose concat)
    if r in sections_src:
        used.add(r)

unused = declared - used
print(f"\n📌 Rule të përdorura në prompt_sections.py: {len(used)}")
for r in sorted(used):
    print(f"   ✅ {r}")

print(f"\n📌 Rule TË PASHFAQURA në prompt_sections.py: {len(unused)}")
for r in sorted(unused):
    print(f"   🗑️  {r}")

# 3. Kontrollo ku përdoren orphans (mundësisht në ANALIZO prompts)
orphans = sorted(unused)
if orphans:
    print(f"\n📌 Ku përdoren orphans kudo në app/:")
    for r in orphans:
        hits = []
        for f in (Path(__file__).resolve().parent.parent / "app").rglob("*.py"):
            if "__pycache__" in str(f):
                continue
            if f.name == "prompt_rules.py":
                continue
            try:
                txt = f.read_text(encoding="utf-8")
            except Exception:
                continue
            if r in txt:
                rel = str(f.relative_to(Path(__file__).resolve().parent.parent)).replace("\\", "/")
                hits.append(rel)
        if hits:
            print(f"   ▶ {r}:")
            for h in hits:
                print(f"       {h}")
        else:
            print(f"   ▶ {r}: (askund jashtë prompt_rules.py)")

sys.exit(0)