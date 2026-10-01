# FILE: backend/scripts/test_optimize_query.py
"""
V282.34: Teste për _optimize_query — verifikon bug-un e backspace (B1).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.albanian_rag_service import AlbanianRAGService

svc = AlbanianRAGService.__new__(AlbanianRAGService)

# Test 1: backspace bug — nuk duhet karakter 0x08 në output
q1 = "çfarë thotë LMD për dëmshpërblim?"
out1 = svc._optimize_query(q1)
assert "\x08" not in out1, f"BACKSPACE (0x08) mbetur ne: {out1!r}"
assert "LMD (Ligji për Marrëdhëniet e Detyrimeve)" in out1, f"Expansion mungon: {out1!r}"
print(f"OK T1 (LMD)   -> {out1!r}")

# Test 2: shumë akronime njëherësh — verifiko prezencën individuale
q2 = "KPRK dhe LPK dhe LFK"
out2 = svc._optimize_query(q2)
assert "\x08" not in out2, f"BACKSPACE ne: {out2!r}"
assert "KPRK (Kodi Penal" in out2, f"KPRK nuk u expandua: {out2!r}"
assert "LPK (Ligji për Procedurën Kontestimore)" in out2, f"LPK nuk u expandua: {out2!r}"
assert "LFK (Ligji për Familjen i Kosovës)" in out2, f"LFK nuk u expandua: {out2!r}"
print(f"OK T2 (multi) -> {out2!r}")

# Test 3: akronim brenda fjale (nuk duhet expanduar)
q3 = "LMDS nuk është akronim"
out3 = svc._optimize_query(q3)
assert "LMDS (Ligji" not in out3, f"Word-boundary i prishur: {out3!r}"
print(f"OK T3 (bound) -> {out3!r}")

# Test 4: preamble heqje
q4 = "më trego rreth neneve"
out4 = svc._optimize_query(q4)
assert not out4.lower().startswith("më trego"), f"Preamble mbetur: {out4!r}"
print(f"OK T4 (preamb)-> {out4!r}")

print("\nTE GJITHA TESTET KALUAN")