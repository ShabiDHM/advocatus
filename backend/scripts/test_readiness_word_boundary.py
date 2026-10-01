# FILE: backend/scripts/test_readiness_word_boundary.py
"""
V282.34: Verifikon që _replace_body_verdict nuk korrupton fjalë që
përmbajnë "Gati" si substring (p.sh. "Gatishmëria").
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.document_review.verify.readiness import _replace_body_verdict

# T1: fjalë e plotë "GATI"
t1 = "### A. Vlerësimi\nGATI — Gati për dorëzim\n"
out1 = _replace_body_verdict(t1, "KËRKON PUNË")
assert "~~GATI~~" in out1, f"Fjala 'GATI' nuk u zëvendësua: {out1!r}"
print(f"OK T1: 'GATI' u zëvendësua")

# T2 (bug-u origjinal): 'Gatishmëria' nuk duhet të preket
t2 = "Gatishmëria e draftit është e mirë."
out2 = _replace_body_verdict(t2, "KËRKON PUNË")
assert "~~Gati~~" not in out2, f"BUG: 'Gatishmëria' u korruptua: {out2!r}"
assert "Gatishmëria" in out2, f"Fjala humbi: {out2!r}"
print(f"OK T2: 'Gatishmëria' nuk u prek")

# T3: 'Gatishmërinë' (trajta e shquar) nuk duhet të preket
t3 = "Gatishmërinë e vlerësojmë si të mirë."
out3 = _replace_body_verdict(t3, "KËRKON PUNË")
assert "~~Gati~~" not in out3, f"BUG: 'Gatishmërinë' u korruptua: {out3!r}"
print(f"OK T3: 'Gatishmërinë' nuk u prek")

# T4: 'GATI' në mes të fjalisë
t4 = "Rezultati: GATI sipas vlerësimit paraprak."
out4 = _replace_body_verdict(t4, "KËRKON PUNË")
assert "~~GATI~~" in out4, f"Mes fjale nuk u zëvendësua: {out4!r}"
print(f"OK T4: 'GATI' në mes të fjalisë u zëvendësua")

# T5: count=1 — vetëm dukurja e parë
t5 = "GATI është verdikti. GATI përsëritet."
out5 = _replace_body_verdict(t5, "KËRKON PUNË")
assert out5.count("~~GATI~~") == 1, f"Duhet vetëm 1 zëvendësim: {out5!r}"
print(f"OK T5: count=1 ruhet")

# T6: 'Gatishmëria' në fillim të rreshtit nuk duhet të preket
t6 = "Gatishmëria\nGATI — gati"
out6 = _replace_body_verdict(t6, "KËRKON PUNË")
assert out6.startswith("Gatishmëria"), f"Fillimi u prek: {out6!r}"
assert "~~GATI~~" in out6, f"Verdikti nuk u zëvendësua: {out6!r}"
print(f"OK T6: kombinim 'Gatishmëria' + 'GATI' u trajtua saktë")

print(f"\n{'=' * 60}\nTË GJITHA TESTET KALUAN\n{'=' * 60}")