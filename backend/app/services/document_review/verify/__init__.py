# FILE: backend/app/services/document_review/verify/__init__.py
# PHOENIX PROTOCOL - VERIFY PACKAGE V1.1
#
# V1.1: VERSION RECONCILIATION —
#       - `__version__` dhe header sinkronizohen me modulin kryesor
#         `verifier.py` (V2.6 aktual). Më parë: V1.0.0 me header stale
#         "ekstraktim nga draft_verifier.py V1.17" — edhe pse moduli ka
#         evoluar në V2.6.
# V1.0: Modul i modularizuar për DraftVerifier.
#
# Struktura:
#   config.py           — Konstantet (readiness, markers, gate, keywords)
#   cited_summary.py    — Përmbledhje e precedentëve të cituar + ekstraktim
#   warnings.py         — Bannerat (hallucination, cited precedents, override)
#   readiness.py        — Parse + override i gatishmërisë
#   scoring.py          — Llogaritja e skorit + formal_pct
#   section_builders.py — Ndërtuesit Python të seksioneve (A, 3.A)
#   report_builder.py   — Raporti final + empty result
#   persistence.py      — Ruajtja në MongoDB
#   verifier.py         — Entry point (DraftVerifier, get_draft_verifier)

__version__ = "2.6.0"