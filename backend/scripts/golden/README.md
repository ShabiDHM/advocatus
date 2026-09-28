# Golden Dataset — Juristi AI

Set testesh të vërteta për të matur saktësinë e pipeline-it.

## Struktura

scripts/golden/
├── README.md                        ← ky file
├── documents/                       ← dokumentet test (PDF/DOCX)
│   └── vendim_urdher_mbrojtje.pdf
└── expected/                        ← vlerat e pritura
    └── vendim_urdher_mbrojtje.json

## Si funksionon

1. `documents/` ka dokumente reale.
2. `expected/` ka JSON për secilin dokument me vlerat e pritura (numri minimal i neneve, ligjeve, datave, forensik rule IDs, etj.).
3. `scripts/run_golden.py` ekzekuton VETËM pjesët deterministe (citation_extractor, fact_extractor) dhe krahason me `expected/`.
4. Printon PASS/FAIL për secilin dokument.

## Pse pa LLM?

- LLM kushton para → nuk mund të testosh shpesh.
- Deterministi mbulon ~70% e bug-ve (ekstraktim, forensik, kontradikta).
- Testi deterministik është <2 sekonda.

## Si të shtosh dokument të re

1. Vendos PDF në `documents/`.
2. Kopjo një `expected/*.json` ekzistues si template.
3. Plotëso vlerat e pritura (shiko skemën më poshtë).
4. Ekzekuto: `python scripts/run_golden.py`

## Skema e expected/*.json

```json
{
  "file_name": "vendim_urdher_mbrojtje.pdf",
  "document_type": "Vendim Gjyqësor",
  "min_thresholds": {
    "articles": 5,
    "laws_by_number": 1,
    "case_numbers": 1,
    "dates": 5,
    "deadlines": 1,
    "parties": 5,
    "dispositive_points": 3
  },
  "expected_forensic_rules_any": [
    "Mospërputhje dispozitiv-arsyetim"
  ],
  "expected_forensic_rules_min_count": 1,
  "notes": "Vendim real nga Gjykata Themelore Prishtinë"
}
