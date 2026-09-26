# FILE: backend/app/services/pillars/cross_reference_service.py
# PHOENIX PROTOCOL - CROSS-REFERENCE SERVICE V1.1
# V1.1: (1) Hequr dead imports: Counter, Tuple, ObjectId.
#       (2) FIX — _build_document_references përdor VETËM entitetet e tekstit
#           (CASE_NUMBER) për mentioned_cns. Më parë përfshinte edhe
#           metadata.case_number të vetë dokumentit, duke krijuar lidhje
#           N×(N-1) të rreme për dokumente me të njëjtin case_number.
# V1.0: Builds relationships between documents in a legal case.

import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


CROSS_REF_COLLECTION = "case_cross_references"
EXTRACTION_COLLECTION = "case_extractions"


class CrossReferenceService:
    """
    Analizon lidhjet midis dokumenteve të një fashikulli.

    Llojet e lidhjeve:
    - document_references:  docs që përmendin numra lënde të tjerë
    - case_number_chain:    {case_number: [doc_ids]}
    - party_appearances:    {party_name: [doc_ids]}
    - statute_citations:    {statute: [doc_ids]}
    - date_alignment:       docs me data të njëjta/të afërta
    - chronological_chain:  renditje kohore e ngjarjeve
    """

    def __init__(self, db):
        self.db = db

    # ────────────────────────────────────────────────────────────────────
    # PUBLIC — build
    # ────────────────────────────────────────────────────────────────────

    def build(self, case_id: str) -> Dict[str, Any]:
        start = time.time()

        extractions = self._load_extractions(case_id)
        if not extractions:
            return self._empty_result(case_id, "No extractions found for this case.")

        docs_by_id: Dict[str, Dict[str, Any]] = {
            e["document_id"]: e for e in extractions
        }

        case_number_chain = self._build_case_number_chain(extractions)
        party_appearances = self._build_party_appearances(extractions)
        statute_citations = self._build_statute_citations(extractions)
        date_alignment = self._build_date_alignment(extractions)
        chronological = self._build_chronological_chain(extractions)
        document_refs = self._build_document_references(
            extractions, case_number_chain, docs_by_id
        )

        total_rels = (
            len(document_refs)
            + sum(len(v) for v in party_appearances.values())
            + sum(len(v) for v in statute_citations.values())
        )

        stats = {
            "case_id": case_id,
            "documents_analyzed": len(extractions),
            "total_relationships": total_rels,
            "unique_case_numbers": len(case_number_chain),
            "unique_parties": len(party_appearances),
            "unique_statutes": len(statute_citations),
            "document_references": len(document_refs),
            "duration_sec": round(time.time() - start, 2),
        }

        result = {
            "case_id": case_id,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "document_references": document_refs,
            "case_number_chain": case_number_chain,
            "party_appearances": party_appearances,
            "statute_citations": statute_citations,
            "date_alignment": date_alignment,
            "chronological_chain": chronological,
            "stats": stats,
            "status": "completed",
        }

        self._persist(result)

        logger.info(
            f"✅ [XREF] Built cross-references for case {case_id}: "
            f"docs={len(extractions)}, rels={total_rels}, "
            f"case_numbers={len(case_number_chain)}, "
            f"parties={len(party_appearances)}, "
            f"statutes={len(statute_citations)}, "
            f"duration={stats['duration_sec']}s"
        )

        return result

    # ────────────────────────────────────────────────────────────────────
    # INTERNAL — load
    # ────────────────────────────────────────────────────────────────────

    def _load_extractions(self, case_id: str) -> List[Dict[str, Any]]:
        try:
            cursor = self.db[EXTRACTION_COLLECTION].find({
                "case_id": str(case_id),
                "status": "completed",
            }).sort([("completed_at", 1)])
            return list(cursor)
        except Exception as e:
            logger.error(f"❌ [XREF] load_extractions failed: {e}")
            return []

    def _empty_result(self, case_id: str, reason: str) -> Dict[str, Any]:
        return {
            "case_id": case_id,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "document_references": [],
            "case_number_chain": {},
            "party_appearances": {},
            "statute_citations": {},
            "date_alignment": {},
            "chronological_chain": [],
            "stats": {
                "case_id": case_id,
                "documents_analyzed": 0,
                "total_relationships": 0,
                "duration_sec": 0.0,
            },
            "status": "empty",
            "warning": reason,
        }

    # ────────────────────────────────────────────────────────────────────
    # INTERNAL — case number chain
    # ────────────────────────────────────────────────────────────────────

    def _build_case_number_chain(
        self,
        extractions: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        chain: Dict[str, List[str]] = defaultdict(list)

        for ext in extractions:
            doc_id = ext["document_id"]
            seen_in_doc = set()

            for e in ext.get("entities_by_type", {}).get("CASE_NUMBER", []):
                text = (e.get("text") or "").strip()
                if text and text not in seen_in_doc:
                    chain[text].append(doc_id)
                    seen_in_doc.add(text)

            meta_cn = (ext.get("metadata") or {}).get("case_number")
            if meta_cn and meta_cn not in seen_in_doc:
                chain[meta_cn].append(doc_id)
                seen_in_doc.add(meta_cn)

        return dict(chain)

    # ────────────────────────────────────────────────────────────────────
    # INTERNAL — party appearances
    # ────────────────────────────────────────────────────────────────────

    def _build_party_appearances(
        self,
        extractions: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        appearances: Dict[str, List[str]] = defaultdict(list)

        for ext in extractions:
            doc_id = ext["document_id"]
            seen_in_doc = set()

            for label in ["PARTY", "JUDGE", "PROSECUTOR", "LAWYER", "WITNESS"]:
                for e in ext.get("entities_by_type", {}).get(label, []):
                    name = (e.get("text") or "").strip()
                    if not name:
                        continue
                    key = name.lower()
                    if key in seen_in_doc:
                        continue
                    appearances[name].append({
                        "document_id": doc_id,
                        "role": label,
                    })
                    seen_in_doc.add(key)

            for p in (ext.get("metadata") or {}).get("parties", []):
                if not isinstance(p, dict):
                    continue
                name = (p.get("name") or "").strip()
                role_meta = (p.get("role") or "").strip()
                if not name:
                    continue
                key = name.lower()
                if key in seen_in_doc:
                    continue
                appearances[name].append({
                    "document_id": doc_id,
                    "role": "PARTY",
                    "meta_role": role_meta,
                })
                seen_in_doc.add(key)

        result: Dict[str, List[str]] = {}
        for name, items in appearances.items():
            result[name] = sorted(set(i["document_id"] for i in items))

        return result

    # ────────────────────────────────────────────────────────────────────
    # INTERNAL — statute citations
    # ────────────────────────────────────────────────────────────────────

    def _build_statute_citations(
        self,
        extractions: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        citations: Dict[str, List[str]] = defaultdict(list)

        for ext in extractions:
            doc_id = ext["document_id"]

            for e in ext.get("entities_by_type", {}).get("STATUTE", []):
                text = (e.get("text") or "").strip()
                if text:
                    citations[text].append(doc_id)

            for e in ext.get("entities_by_type", {}).get("ARTICLE", []):
                text = (e.get("text") or "").strip()
                if text:
                    citations[text].append(doc_id)

            for st in (ext.get("metadata") or {}).get("statute", []):
                if st:
                    citations[str(st).strip()].append(doc_id)
            for art in (ext.get("metadata") or {}).get("articles", []):
                if art:
                    citations[str(art).strip()].append(doc_id)

        result: Dict[str, List[str]] = {}
        for key, docs in citations.items():
            result[key] = sorted(set(docs))

        return result

    # ────────────────────────────────────────────────────────────────────
    # INTERNAL — date alignment
    # ────────────────────────────────────────────────────────────────────

    def _build_date_alignment(
        self,
        extractions: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        alignment: Dict[str, List[str]] = defaultdict(list)

        for ext in extractions:
            doc_id = ext["document_id"]
            seen_in_doc = set()

            for e in ext.get("entities_by_type", {}).get("DATE", []):
                text = (e.get("text") or "").strip()
                if text and text not in seen_in_doc:
                    alignment[text].append(doc_id)
                    seen_in_doc.add(text)

            meta_date = (ext.get("metadata") or {}).get("date")
            if meta_date and meta_date not in seen_in_doc:
                alignment[meta_date].append(doc_id)

        result: Dict[str, List[str]] = {}
        for key, docs in alignment.items():
            unique_docs = sorted(set(docs))
            if len(unique_docs) > 1:
                result[key] = unique_docs

        return result

    # ────────────────────────────────────────────────────────────────────
    # INTERNAL — chronological chain
    # ────────────────────────────────────────────────────────────────────

    def _build_chronological_chain(
        self,
        extractions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []

        for ext in extractions:
            meta = ext.get("metadata") or {}
            date_str = meta.get("date") or ext.get("completed_at")
            items.append({
                "document_id": ext["document_id"],
                "file_name": ext.get("file_name"),
                "document_type": ext.get("document_type"),
                "date": date_str,
                "entities_count": ext.get("stats", {}).get("total_entities", 0),
            })

        def _sort_key(item):
            d = item.get("date") or ""
            parts = d.split(".")
            if len(parts) == 3:
                try:
                    return (0, int(parts[2]), int(parts[1]), int(parts[0]))
                except ValueError:
                    pass
            return (1, 0, 0, 0)

        items.sort(key=_sort_key)
        return items

    # ────────────────────────────────────────────────────────────────────
    # INTERNAL — document references
    # ────────────────────────────────────────────────────────────────────

    def _build_document_references(
        self,
        extractions: List[Dict[str, Any]],
        case_number_chain: Dict[str, List[str]],
        docs_by_id: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Lidhjet dokument→dokument kur një dokument PËRMEND (në tekst)
        numrin e lëndës së një tjetri.

        V1.1: NUK përfshihet metadata.case_number i dokumentit burim —
              ajo është identifikuesi i vetë dokumentit, nuk është "përmendje".
              Kjo eliminon lidhjet N×(N-1) për dokumente me të njëjtin case_number.
        """
        cn_to_primary: Dict[str, List[str]] = defaultdict(list)
        for ext in extractions:
            doc_id = ext["document_id"]
            meta_cn = (ext.get("metadata") or {}).get("case_number")
            if meta_cn:
                cn_to_primary[meta_cn].append(doc_id)

        refs: List[Dict[str, Any]] = []
        seen_pairs = set()

        for ext in extractions:
            source_doc = ext["document_id"]
            source_name = ext.get("file_name")

            # V1.1: VETËM entitetet e tekstit — jo metadata
            mentioned_cns = set()
            for e in ext.get("entities_by_type", {}).get("CASE_NUMBER", []):
                text = (e.get("text") or "").strip()
                if text:
                    mentioned_cns.add(text)

            for cn in mentioned_cns:
                targets = cn_to_primary.get(cn, [])
                for target_doc in targets:
                    if target_doc == source_doc:
                        continue
                    key = (source_doc, target_doc, cn)
                    if key in seen_pairs:
                        continue
                    seen_pairs.add(key)
                    refs.append({
                        "source_document_id": source_doc,
                        "source_file_name": source_name,
                        "target_document_id": target_doc,
                        "target_file_name": docs_by_id.get(target_doc, {}).get("file_name"),
                        "via_case_number": cn,
                        "relationship": "MENTIONS_CASE_NUMBER",
                    })

        return refs

    # ────────────────────────────────────────────────────────────────────
    # INTERNAL — persist
    # ────────────────────────────────────────────────────────────────────

    def _persist(self, result: Dict[str, Any]) -> None:
        try:
            self.db[CROSS_REF_COLLECTION].update_one(
                {"case_id": result["case_id"]},
                {"$set": result},
                upsert=True,
            )
        except Exception as e:
            logger.error(f"❌ [XREF] Persist failed for case {result.get('case_id')}: {e}")
            raise

    # ────────────────────────────────────────────────────────────────────
    # PUBLIC — load
    # ────────────────────────────────────────────────────────────────────

    def load(self, case_id: str) -> Optional[Dict[str, Any]]:
        try:
            return self.db[CROSS_REF_COLLECTION].find_one({"case_id": str(case_id)})
        except Exception as e:
            logger.error(f"❌ [XREF] load failed: {e}")
            return None


# ────────────────────────────────────────────────────────────────────────────
# FACTORY
# ────────────────────────────────────────────────────────────────────────────

def get_cross_reference_service(db: Any) -> CrossReferenceService:
    return CrossReferenceService(db)