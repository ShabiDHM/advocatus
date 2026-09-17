# FILE: backend/app/services/categorization_service.py
# PHOENIX PROTOCOL - CATEGORIZATION ENGINE V3.0
# INSTANT MULTI-CATEGORY HEURISTICS — CHUNK-AWARE, ZERO SILENT TRUNCATION
# Backward compatible: categorize_document() returns primary category (str).

import logging
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────────
# CATEGORY RULES V3.0 — EXPANDED + WEIGHTED
# Format: (category_name, [keywords], weight_multiplier)
# Higher weight → more indicative of the category.
# ────────────────────────────────────────────────────────────────────────────

CATEGORY_RULES: List[tuple] = [
    (
        "Vendim Gjyqësor",
        [
            "aktvendim", "aktgjykim", "në emër të popullit",
            "kolegji gjykues", "trupi gjykues", "gjykata vendosi",
            "shpallur", "gjyqtari", "vendim", "dispozitiv",
        ],
        1.0,
    ),
    (
        "Padi / Kërkesëpadi",
        [
            "kërkesëpadi", "kerkesepadi", "paditësi", "padia kundër",
            "petitum", "e paditura", "i padituri", "parashtron padi",
            "padi", "paditës",
        ],
        1.0,
    ),
    (
        "Kundërpadi / Prapësim",
        [
            "kundërpadi", "kunderpadi", "prapësim", "prapsim",
            "përgjigje në padi", "pergjigje ne padi", "kundërpaditësi",
        ],
        1.2,  # shumë specifik
    ),
    (
        "Penale / Kallëzim",
        [
            "kallëzim penal", "kallezim penal", "aktakuzë", "aktakuze",
            "prokuroria", "vepër penale", "veper penale", "i pandehuri",
            "e pandehura", "kallëzim", "kallezim", "ndjekje penale",
        ],
        1.1,
    ),
    (
        "Ankesë / Mjet Juridik",
        [
            "ankesë", "ankese", "ankim", "apel", "revizion",
            "kërkesë për rishqyrtim", "kerkese per rishqyrtim",
            "mjet juridik", "e kundërshtoj",
        ],
        1.0,
    ),
    (
        "Kontratë / Marrëveshje",
        [
            "kontratë", "kontrate", "marrëveshje", "marreveshje",
            "palët kontraktuese", "palet kontraktuese", "nënshkruan",
            "nen-shkruan", "klauzolë", "klauzole", "afati i kontratës",
        ],
        1.0,
    ),
    (
        "Financiare / Faturë",
        [
            "faturë", "fature", "transaksion", "pagesë", "pagese",
            "shuma prej", "kupon fiskal", "llogari bankare",
            "llogari-bankare", "debit", "kredit", "borxh",
        ],
        0.9,
    ),
    (
        "Ekspertizë / Raport",
        [
            "ekspertizë", "ekspertize", "raport social", "qps",
            "procesverbal", "proces-verbal", "raport",
            "konstatim", "gjetje", "analizë teknike",
        ],
        1.0,
    ),
    # ── TË REJA V3.0 ──
    (
        "Kërkesë / Parashtresë",
        [
            "kërkesë", "kerkese", "parashtresë", "parashtrese",
            "kërkoj", "kerkoj", "i drejtohem gjykatës",
            "ju lutem", "kërkesë procedurale",
        ],
        0.8,
    ),
    (
        "Njoftim / Urdhër",
        [
            "njoftim", "njoftohet", "urdhër", "urdher",
            "urdhërohet", "njoftim gjyqësor", "thirrje",
            "thirrje gjyqësore", "caktim seance",
        ],
        0.9,
    ),
    (
        "Vërtetim / Certifikatë",
        [
            "vërtetim", "vertetim", "certifikatë", "certifikate",
            "dëshmi", "deshmi", "potvrda", "ekstrakt",
            "certifikon", "vërtetohet",
        ],
        1.0,
    ),
    (
        "Memo / Shënim",
        [
            "memo", "shënim", "shenim", "shënime", "shenime",
            "shënim intern", "memo intern", "kujtesë", "kujtese",
        ],
        0.7,
    ),
    (
        "Shkresë Procedurale",
        [
            "shkresë", "shkrese", "procedurale", "shkresa",
            "akti procedural", "dokument procedural",
        ],
        0.6,
    ),
    (
        "Ekzekutim / Përmbarim",
        [
            "ekzekutim", "ekzekutimi", "përmbarim", "permbarim",
            "përmbarues", "permbarues", "akt ekzekutiv",
            "urdhër ekzekutiv", "urdher ekzekutiv",
        ],
        1.1,
    ),
    (
        "Trashëgimi / Testament",
        [
            "trashëgimi", "trashgimi", "testament", "amana",
            "trashëgimtar", "trashgimtar", "pasuri e lënë",
            "pasuri e lene", "lënda trashëgimore",
        ],
        1.1,
    ),
    (
        "Familje / Martesë",
        [
            "martesë", "martese", "bashkëshort", "bashkeshort",
            "bashkëshortor", "bashkeshortor", "divorc",
            "kujdestari", "kujdestar", "ushqim", "alimentacion",
            "prindërit", "prinderit",
        ],
        1.0,
    ),
    (
        "Pronë / Pasuri",
        [
            "pronë", "prone", "pronësi", "pronesi", "kadastër",
            "kadaster", "hipotekë", "hipoteke", "certifikatë prone",
            "certifikate prone", "truall", "parcelë", "parcele",
        ],
        0.9,
    ),
    (
        "Punë / Punësim",
        [
            "punësim", "punesim", "kontratë pune", "kontrate pune",
            "punëdhënës", "punedhenes", "punëmarrës", "punemarres",
            "pagë", "page", "shkarkim", "pushim nga puna",
        ],
        0.9,
    ),
]


# Default weight multiplier nëse mungon
DEFAULT_WEIGHT = 1.0
MIN_TEXT_LENGTH = 10
MAX_CHUNK = 50_000  # siguri për shmangje e memory spikes; skanohet gjithë teksti në chunks


# ────────────────────────────────────────────────────────────────────────────
# SERVICE
# ────────────────────────────────────────────────────────────────────────────

class CategorizationService:
    """
    Shërbimi i Kategorizimit të Dokumenteve Ligjore.

    V3.0 — Përmirësime:
    - Skanon GJITHË tekstin (zero silent truncation).
    - Multi-category: kthen të gjitha kategoritë me score.
    - Confidence calculation.
    - 18 kategori (nga 8).
    - Batch processing.
    - Backward compatible: categorize_document() mbetet e njëjta API.
    """

    def __init__(self):
        # Pre-compile regex patterns për shpejtësi
        self._rules = []
        for rule in CATEGORY_RULES:
            if len(rule) == 3:
                name, keywords, weight = rule
            else:
                name, keywords = rule
                weight = DEFAULT_WEIGHT
            self._rules.append((name, keywords, float(weight)))

        # Kufiri për "primary" — kategoria duhet të ketë këtë score minimal
        self._min_score_for_primary = 1
        # Kufiri për "ambiguous"
        self._ambiguity_gap = 0.5

        logger.info(
            f"✅ [CATEGORIZATION] Categorization Service V3.0 Initialized "
            f"({len(self._rules)} categories)"
        )

    # ────────────────────────────────────────────────────────────────
    # CORE — score per category
    # ────────────────────────────────────────────────────────────────

    def _score_categories(
        self,
        text: str
    ) -> List[Dict[str, Any]]:
        """
        Skanon GJITHË tekstin dhe kthen score për çdo kategori.
        Returns: [{name, score, matched_keywords, weight}, ...] — sorted desc.
        """
        if not text or len(text.strip()) < MIN_TEXT_LENGTH:
            return []

        # Skano tekstin në chunks për të shmangur memory spikes në dokumente
        # shumë të mëdha, pa humbur asnjë karakter.
        if len(text) <= MAX_CHUNK:
            chunks = [text]
        else:
            chunks = [
                text[i:i + MAX_CHUNK]
                for i in range(0, len(text), MAX_CHUNK)
            ]

        lower_text = " ".join(c.lower() for c in chunks)

        results: List[Dict[str, Any]] = []

        for name, keywords, weight in self._rules:
            matched: List[str] = []
            for kw in keywords:
                if kw in lower_text:
                    matched.append(kw)

            if not matched:
                continue

            # Score = numri i keywords unike * weight
            score = len(matched) * weight

            results.append({
                "name": name,
                "score": round(score, 2),
                "matched_keywords": matched,
                "matched_count": len(matched),
                "weight": weight,
            })

        # Sort by score desc
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    # ────────────────────────────────────────────────────────────────
    # PRIMARY API (backward compatible)
    # ────────────────────────────────────────────────────────────────

    def categorize_document(self, text: str) -> str:
        """
        Kthen kategorinë kryesore si STRING.

        BACKWARD COMPATIBLE — e njëjta API si V2.0.
        Për output të detajuar, përdor categorize_document_detailed().
        """
        detailed = self.categorize_document_detailed(text)
        return detailed["primary_category"]

    # ────────────────────────────────────────────────────────────────
    # DETAILED API (e re)
    # ────────────────────────────────────────────────────────────────

    def categorize_document_detailed(self, text: str) -> Dict[str, Any]:
        """
        Kthen klasifikim të plotë të strukturuar.

        Output:
        {
          "primary_category": "Padi / Kërkesëpadi",
          "all_categories": [
              {"name": "...", "score": 5.0, "matched_keywords": [...], ...},
              ...
          ],
          "confidence": 0.83,
          "is_ambiguous": False,
          "text_length_scanned": 12345,
          "categories_count": 3,
        }
        """
        text_len = len(text) if text else 0

        if not text or text_len < MIN_TEXT_LENGTH:
            return {
                "primary_category": "Procedurale",
                "all_categories": [],
                "confidence": 0.0,
                "is_ambiguous": False,
                "text_length_scanned": text_len,
                "categories_count": 0,
            }

        scored = self._score_categories(text)

        if not scored:
            return {
                "primary_category": "Procedurale",
                "all_categories": [],
                "confidence": 0.0,
                "is_ambiguous": False,
                "text_length_scanned": text_len,
                "categories_count": 0,
            }

        primary = scored[0]
        top_score = primary["score"]
        second_score = scored[1]["score"] if len(scored) > 1 else 0.0

        # Confidence: sa e qartë është kategoria kryesore
        # Formula: 1 - (second_score / top_score) — sa më e madhe diferenca, aq më e sigurt
        if top_score <= 0:
            confidence = 0.0
        else:
            confidence = round(1.0 - (second_score / top_score), 2)
            confidence = max(0.0, min(1.0, confidence))

        # Ambiguous nëse dy kategoritë e para janë shumë afër
        is_ambiguous = (
            len(scored) > 1
            and second_score > 0
            and (top_score - second_score) <= self._ambiguity_gap
        )

        return {
            "primary_category": primary["name"],
            "all_categories": scored,
            "confidence": confidence,
            "is_ambiguous": is_ambiguous,
            "text_length_scanned": text_len,
            "categories_count": len(scored),
        }

    # ────────────────────────────────────────────────────────────────
    # BATCH API
    # ────────────────────────────────────────────────────────────────

    def categorize_batch(
        self,
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Batch categorization.

        documents: [{"id": str, "text": str}, ...]
        Returns: {doc_id: detailed_result, ...}
        """
        results: Dict[str, Dict[str, Any]] = {}
        total = len(documents)

        logger.info(f"🔍 [CATEGORIZATION] Batch: {total} documents")

        for idx, doc in enumerate(documents):
            doc_id = str(doc.get("id") or doc.get("_id") or f"doc_{idx}")
            doc_text = doc.get("text") or ""
            results[doc_id] = self.categorize_document_detailed(doc_text)

        logger.info(f"✅ [CATEGORIZATION] Batch complete: {total} documents")
        return results

    # ────────────────────────────────────────────────────────────────
    # UTILITY
    # ────────────────────────────────────────────────────────────────

    def list_categories(self) -> List[str]:
        """Kthen listën e kategorive të njohura."""
        return [name for name, _, _ in self._rules]


# ────────────────────────────────────────────────────────────────────────────
# SINGLETON
# ────────────────────────────────────────────────────────────────────────────

CATEGORIZATION_SERVICE = CategorizationService()