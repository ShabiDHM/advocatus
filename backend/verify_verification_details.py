# FILE: backend/verify_verification_details.py
# Grep për konsumatorë të verification_details.
# Ekzekuto: python verify_verification_details.py   (nga backend/)
# Fshi pas përdorimit.

import re
from pathlib import Path

BACKEND = Path(__file__).parent.resolve()
ROOT = BACKEND.parent
FRONTEND = ROOT / "frontend"

SCAN_DIRS = [
    (BACKEND / "app", "BACKEND / app"),
    (FRONTEND / "src", "FRONTEND / src"),
]

TOKENS = [
    "verification_details",
    "citation_profile",
    "fact_profile",
    "verification_report",
]


def main():
    print("=" * 78)
    print("KONSUMATORË TË verification_details / profiles")
    print("=" * 78)

    for base, label in SCAN_DIRS:
        print(f"\n### {label}")
        print("-" * 78)
        if not base.exists():
            print("  [SKIP]")
            continue
        exts = ("*.ts", "*.tsx") if "FRONTEND" in label else ("*.py",)
        hits = 0
        for ext in exts:
            for f in base.rglob(ext):
                parts = set(f.parts)
                if "__pycache__" in parts or "_legacy" in parts:
                    continue
                try:
                    text = f.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                rel = f.relative_to(ROOT)
                for i, line in enumerate(text.splitlines(), start=1):
                    s = line.strip()
                    if s.startswith("#") or s.startswith("//"):
                        continue
                    for tok in TOKENS:
                        if re.search(rf"\b{re.escape(tok)}\b", s):
                            # Skip header comment and self-reference
                            if "verify_verification_details" in str(rel):
                                continue
                            print(f"  [{tok}] {rel}:{i}: {s[:120]}")
                            hits += 1
                            break
        if hits == 0:
            print("  ✅ Pa konsumatorë.")
        else:
            print(f"\n  Gjithsej {hits} hits.")


if __name__ == "__main__":
    main()