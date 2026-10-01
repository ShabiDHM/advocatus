# backend/scripts/test_batch_3fix.py
"""V282.34: Verifikon 3 fixet e batch-it."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "app/services/document_review"


def strip_comments(src: str) -> str:
    """Heq komentet (# ...) nga kodi për të shmangur false positives."""
    return "\n".join(
        line for line in src.split("\n")
        if not line.strip().startswith("#")
    )


# ─── Fix 1: case_profile DELETED filter ───
cp = (ROOT / "case_profile.py").read_text(encoding="utf-8")
cp_code = strip_comments(cp)
assert '"$ne": "DELETED"' in cp_code, "case_profile: mungon DELETED filter"
assert 'str(case_oid)}' not in cp_code, "case_profile: str(case_oid) në KOD (jo koment)"
assert "V1.1" in cp, "case_profile: version nuk u përditësua"
print("OK case_profile.py V1.1: DELETED filter + redundancy hequr")

# ─── Fix 2: streaming role-neutral ───
st = (ROOT / "streaming.py").read_text(encoding="utf-8")
st_code = strip_comments(st)
assert "AUDITOJE atë" not in st_code, "streaming: 'AUDITOJE atë' në KOD"
assert "V1.4" in st, "streaming: version nuk u përditësua"
assert "MOS përsërit faktet — INTERPRETOJI" in st_code, "streaming: instruction neutral mungon"
print("OK streaming.py V1.4: role-neutral wrapper")

# ─── Fix 3: persistence empty_result enriched ───
pe = (ROOT / "persistence.py").read_text(encoding="utf-8")
pe_code = strip_comments(pe)
assert '"full_report"' in pe_code, "persistence: full_report mungon në empty_result"
assert '"readiness": "UNKNOWN"' in pe_code, "persistence: readiness mungon"
assert '"section_stats"' in pe_code, "persistence: section_stats mungon"
assert "V2.2" in pe, "persistence: version nuk u përditësua"
print("OK persistence.py V2.2: empty_result enriched")

print("\nTË GJITHA TESTET KALUAN")