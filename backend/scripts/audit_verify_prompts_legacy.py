# FILE: backend/scripts/audit_verify_prompts_legacy.py
"""
V282.34: Zbulon kush importon verify_prompts.py (monoliti legacy).
"""
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
APP = BACKEND / "app"

print(f"\n{'=' * 70}")
print("AUDIT — Kush importon `verify_prompts`?")
print(f"{'=' * 70}")

hits = []
for f in APP.rglob("*.py"):
    if "__pycache__" in str(f):
        continue
    try:
        txt = f.read_text(encoding="utf-8")
    except Exception:
        continue
    if "verify_prompts" in txt and "prompt_" not in f.name:  # exclude self
        rel = str(f.relative_to(BACKEND)).replace("\\", "/")
        cnt = txt.count("verify_prompts")
        hits.append((rel, cnt))

if hits:
    for rel, cnt in sorted(hits):
        print(f"  ▶ {rel}  ({cnt} hits)")
else:
    print("  (asnjë)")

# Madhësia e monolitit
mono = APP / "services" / "document_review" / "verify_prompts.py"
if mono.exists():
    lines = len(mono.read_text(encoding="utf-8").splitlines())
    print(f"\n📦 verify_prompts.py: {lines} rreshta")