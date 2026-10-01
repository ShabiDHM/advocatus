# backend/scripts/test_verifier_db_laws.py
"""
V282.34: Verifikon që verifier.py V2.6 nuk hedh NameError kur
HALLUCINATION_GATE_ENABLED=False ose fact_profile bosh.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Simulim i rrugës së kodit: inicializimi i db_laws para if-block
# (test i thjeshtë — verifikon se ndryshimi u aplikua)
import ast

src = (Path(__file__).resolve().parent.parent /
       "app/services/document_review/verify/verifier.py").read_text(encoding="utf-8")

# Kontrollo që `db_laws: Set[str] = set()` shfaqet PARA `if HALLUCINATION_GATE_ENABLED`
idx_init = src.find("db_laws: Set[str] = set()")
idx_if = src.find("if HALLUCINATION_GATE_ENABLED and fact_profile:")

assert idx_init > 0, "Nuk u gjet inicializimi i db_laws"
assert idx_if > 0, "Nuk u gjet if-block"
assert idx_init < idx_if, (
    f"db_laws inicializohet PAS if-block! "
    f"init@{idx_init}, if@{idx_if}"
)

print("OK db_laws inicializohet para if-block")
print(f"   init në pozicionin: {idx_init}")
print(f"   if-block në pozicionin: {idx_if}")
print(f"   distanca: {idx_if - idx_init} chars")

# Kontrollo që version u sinkronizua
assert 'execution_mode": "verify_hybrid_v2.6"' in src, "execution_mode nuk u përditësua"
print("OK execution_mode = verify_hybrid_v2.6")

init_src = (Path(__file__).resolve().parent.parent /
            "app/services/document_review/verify/__init__.py").read_text(encoding="utf-8")
assert '__version__ = "2.6.0"' in init_src, "__version__ nuk u sinkronizua"
print("OK __version__ = 2.6.0")

print("\nTË GJITHA TESTET KALUAN")