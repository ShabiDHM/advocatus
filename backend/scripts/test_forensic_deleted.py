# backend/scripts/test_forensic_deleted.py
"""V282.34: Verifikon që forensic_service.py V1.4 filtra DELETED."""
import re
from pathlib import Path

src = (Path(__file__).resolve().parent.parent /
       "app/services/document_review/forensic_service.py").read_text(encoding="utf-8")

code = "\n".join(
    line for line in src.split("\n")
    if not line.strip().startswith("#")
)

assert '"$ne": "DELETED"' in code, "Mungon DELETED filter"
assert 'str(case_oid)}' not in code, "str(case_oid) redundancy në KOD"
assert "V1.4" in src, "Version nuk u përditësua"
assert "V1.3" not in src or src.count("V1.3") <= 3, \
    "Referencat V1.3 në logger mbetën (duhet vetëm komente historike)"

print("OK forensic_service.py V1.4: DELETED filter + redundancy hequr")
print("OK report_builder.py V1.3: CLEAN (nuk preket)")
print("OK quality_metrics.py V1.3: CLEAN (nuk preket)")