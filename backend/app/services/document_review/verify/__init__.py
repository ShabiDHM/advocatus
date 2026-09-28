# FILE: backend/app/services/document_review/verify/__init__.py
# PHOENIX PROTOCOL - VERIFY PACKAGE V1.0
# Modul i modularizuar për DraftVerifier.
# HAPI A: ekstraktim pa ndryshim logjike nga draft_verifier.py V1.17.
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
#
# Eksportet shtohen gradualisht pasi modulet të mbushen.

__version__ = "1.0.0"