# FILE: backend/app/services/ontology_service.py
# PHOENIX PROTOCOL - PURE LEGAL FACT & STATEMENT ONTOLOGY (ZERO DOCUMENT NODES)

import logging
import re
import io
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from pymongo.database import Database
from bson import ObjectId

from .llm_service import _call_llm_async, clean_and_parse_json, FAST_MODEL

logger = logging.getLogger(__name__)

class OntologyService:
    """
    Pure Evidentiary Statement & Contradiction Graph Engine.
    PDFs and sessions are stored strictly as metadata properties, not as central visual clutter nodes.
    """

    def _clean_name(self, name: str) -> str:
        if not name:
            return ""
        clean = name.strip()
        prefixes = [
            r"^(i|e)\s+pandehur(i|a)\s+",
            r"^(i|e)\s+dëmtuar(i|a)\s+",
            r"^paditës(i|ja)\s+",
            r"^i\s+paditur(i)?\s+",
            r"^dëshmitar(i|ja)\s+",
            r"^avokat(i|e)?\s+",
            r"^prokuror(i|e)?\s+",
            r"^gjyqtar(i|e)?\s+",
            r"^ekspert(i)?\s+",
            r"^dr\.\s+",
            r"^prof\.\s+"
        ]
        for p in prefixes:
            clean = re.sub(p, "", clean, flags=re.IGNORECASE)
        return clean.strip()

    def pack_documents_into_dynamic_buckets(self, docs: List[Dict[str, Any]], max_chars_per_bucket: int = 45000) -> List[Dict[str, Any]]:
        buckets = []
        current_bucket_docs = []
        current_bucket_text = []
        current_chars = 0

        for doc in docs:
            doc_id = str(doc.get("_id"))
            doc_name = doc.get("file_name", "Dokument").strip()
            txt = doc.get("extracted_text") or doc.get("text_content") or doc.get("summary") or ""
            
            if not txt.strip():
                continue

            doc_block = f"\n=== BURIMI: {doc_name} (ID: {doc_id}) ===\n{txt}\n"
            block_len = len(doc_block)

            if current_chars + block_len > max_chars_per_bucket and current_bucket_docs:
                buckets.append({
                    "batch_id": len(buckets) + 1,
                    "doc_ids": current_bucket_docs,
                    "combined_text": "".join(current_bucket_text)
                })
                current_bucket_docs = [doc_id]
                current_bucket_text = [doc_block]
                current_chars = block_len
            else:
                current_bucket_docs.append(doc_id)
                current_bucket_text.append(doc_block)
                current_chars += block_len

        if current_bucket_docs:
            buckets.append({
                "batch_id": len(buckets) + 1,
                "doc_ids": current_bucket_docs,
                "combined_text": "".join(current_bucket_text)
            })

        return buckets

    async def extract_ontology_from_batch_async(self, combined_text: str, doc_ids: List[str]) -> Dict[str, Any]:
        if not combined_text.strip():
            return {"nodes": [], "edges": []}

        system_prompt = """
        Ti je një motor i Inteligjencës Artificiale i specializuar në Strukturimin Dinamik të Grafëve Ligjorë.

        DETYRA KRYESORE:
        Nxirr personat, deklaratat e tyre konkrete dhe faktet nga ky grup shkresash.
        RREPTËSISHT E NDALUAR: Mos krijo nyje për emra skedarësh/PDF-sh (p.sh. 'Seanca 1.pdf' nuk është nyje). Emri i skedarit vendoset VETËM te fusha 'burimi_dokumentit'.

        NYJET E LEJUARA (VETËM KËTO 3 KATEGORI):
        1. Person: {"id": "P_emri", "label": "Person", "properties": {"emri": "Emri Mbiemri", "roli": "I Paditur / Dëshmitar / Paditës"}}
        2. Deklaratë_Në_Seancë: {"id": "D_id", "label": "Deklaratë_Në_Seancë", "properties": {"citat_direkt": "Çfarë deklaroi personi", "burimi_dokumentit": "Emri ekzakt i PDF-së"}}
        3. Fakt_Ngjarje: {"id": "F_id", "label": "Fakt_Ngjarje", "properties": {"përshkrimi": "Ngjarja konkrete", "data": "YYYY-MM-DD ose E papërcaktuar", "vendi": "Lokacioni"}}

        LIDHJET E LEJUARA:
        - [Person] -> KAN_DEKLARUAR -> [Deklaratë_Në_Seancë]
        - [Deklaratë_Në_Seancë] -> I_REFEROHET -> [Fakt_Ngjarje]

        KTHE FORMATIN JSON:
        {
          "nodes": [
            { "id": "P_emri", "label": "Person", "properties": { "emri": "Emri", "roli": "Roli" } },
            { "id": "D_01", "label": "Deklaratë_Në_Seancë", "properties": { "citat_direkt": "Citat", "burimi_dokumentit": "Skedari.pdf" } }
          ],
          "edges": [
            { "source": "P_emri", "target": "D_01", "type": "KAN_DEKLARUAR" }
          ]
        }
        """

        try:
            raw_response = await _call_llm_async(
                system_prompt=system_prompt,
                user_content=combined_text,
                json_mode=True,
                temperature=0.0,
                model=FAST_MODEL
            )
            parsed = clean_and_parse_json(raw_response)
            
            raw_nodes = parsed.get("nodes", [])
            raw_edges = parsed.get("edges", [])

            valid_nodes = []
            for n in raw_nodes:
                props = n.get("properties", {})
                lbl = n.get("label", "Deklaratë_Në_Seancë")
                
                # Përcaktohet emri vizual për shfaqje
                if lbl == "Person":
                    display_name = props.get("emri") or n.get("id")
                    node_type = "PERSON"
                elif lbl == "Fakt_Ngjarje":
                    display_name = props.get("përshkrimi") or "Fakt i Provuar"
                    node_type = "EVENT"
                else:
                    display_name = props.get("citat_direkt") or "Dëshmi në Seancë"
                    node_type = "DOCUMENT"

                valid_nodes.append({
                    "id": str(n.get("id")),
                    "label": display_name[:45],
                    "type": node_type,
                    "description": props.get("citat_direkt") or props.get("përshkrimi") or props.get("roli") or "",
                    "properties": props,
                    "source_doc_ids": doc_ids
                })

            valid_edges = []
            for e in raw_edges:
                src = str(e.get("source", ""))
                tgt = str(e.get("target", ""))
                rel = str(e.get("type") or e.get("relation") or "LIDHJE_LIGJORE").upper().replace(" ", "_")

                if src and tgt and src != tgt:
                    edge_id = f"{src}_{rel}_{tgt}"
                    valid_edges.append({
                        "id": edge_id,
                        "source": src,
                        "target": tgt,
                        "relation": rel,
                        "evidence_text": e.get("properties", {}).get("arsyeja", ""),
                        "properties": e.get("properties", {}),
                        "source_doc_ids": doc_ids
                    })

            return {"nodes": valid_nodes, "edges": valid_edges}

        except Exception as e:
            logger.error(f"Error in extraction: {e}")
            return {"nodes": [], "edges": []}

    def merge_graph_data(self, existing_nodes: List[Dict], existing_edges: List[Dict], 
                         new_nodes: List[Dict], new_edges: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        node_dict = {n["id"]: n for n in existing_nodes}

        for node in new_nodes:
            n_id = node["id"]
            if n_id in node_dict:
                existing = node_dict[n_id]
                existing_docs = set(existing.get("source_doc_ids", []))
                existing_docs.update(node.get("source_doc_ids", []))
                existing["source_doc_ids"] = list(existing_docs)
            else:
                node_dict[n_id] = node

        edge_dict = {e["id"]: e for e in existing_edges}
        for edge in new_edges:
            e_id = edge["id"]
            if e_id not in edge_dict:
                edge_dict[e_id] = edge

        return list(node_dict.values()), list(edge_dict.values())

    async def dynamically_synthesize_cross_document_contradictions(
        self, nodes: List[Dict], edges: List[Dict], case_title: str, all_docs: List[Dict] = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Zbulon kontradiktat direkte midis dëshmive të ndryshme dhe krijon lidhjen 'BIE_NDESH_ME'.
        """
        if not nodes or len(nodes) < 2:
            return nodes, edges

        node_dict = {n["id"]: n for n in nodes}
        all_edges = {e["id"]: e for e in edges}

        # Filtrohen vetëm deklaratat për krahasim
        statements = [n for n in nodes if n["type"] in ["DOCUMENT", "EVENT"]]
        if len(statements) < 2:
            return nodes, edges

        statements_str = "\n".join([
            f"- ID: {s['id']} | Burimi: {s.get('properties', {}).get('burimi_dokumentit', 'N/A')} | Deklarata/Fakti: \"{s.get('description', s['label'])}\""
            for s in statements[:60]
        ])

        prompt = f"""
        Ti je një Hetues Forenzik i Kontradiktave Gjyqësore. Lënda: "{case_title}".

        LISTA E DEKLARATAVE DHE FAKTEVE TË NXJERRA NGA DOKUMENTET:
        {statements_str}

        DETYRA:
        Krahaso këto deklarata. Nëse dy dëshmi bien në kundërshtim të drejtpërdrejtë faktik ose kohor, krijo lidhjen BIE_NDESH_ME midis ID-ve përkatëse.

        KTHE VETËM FORMATIN JSON:
        {{
          "contradictions": [
            {{
              "source": "ID_e_Deklarates_1",
              "target": "ID_e_Deklarates_2",
              "arsyeja": "Shpjegimi i saktë pse këto dy dëshmi mospërputhen"
            }}
          ]
        }}
        """

        try:
            raw = await _call_llm_async(
                system_prompt="Analizo kontradiktat ligjore pa shpikur.",
                user_content=prompt,
                json_mode=True,
                temperature=0.0,
                model=FAST_MODEL
            )
            parsed = clean_and_parse_json(raw)
            contradictions = parsed.get("contradictions", [])

            for c in contradictions:
                src = str(c.get("source", ""))
                tgt = str(c.get("target", ""))
                arsyeja = str(c.get("arsyeja", "Dëshmi kontradiktore"))

                if src in node_dict and tgt in node_dict and src != tgt:
                    edge_id = f"{src}_BIE_NDESH_ME_{tgt}"
                    all_edges[edge_id] = {
                        "id": edge_id,
                        "source": src,
                        "target": tgt,
                        "relation": "BIE_NDESH_ME",
                        "evidence_text": arsyeja,
                        "properties": {"arsyeja": arsyeja},
                        "source_doc_ids": ["CONTRADICTION_ENGINE"]
                    }
        except Exception as e:
            logger.error(f"Error in contradiction synthesis: {e}")

        return list(node_dict.values()), list(all_edges.values())

    def get_case_graph(self, db: Database, case_id: str) -> Dict[str, Any]:
        try:
            graph_record = db.case_graphs.find_one({"case_id": case_id})
            if graph_record and graph_record.get("nodes"):
                return {
                    "nodes": graph_record.get("nodes", []),
                    "edges": graph_record.get("edges", []),
                    "updated_at": graph_record.get("updated_at")
                }
            return {"nodes": [], "edges": [], "updated_at": None}
        except Exception as e:
            logger.error(f"Error fetching graph: {e}")
            return {"nodes": [], "edges": [], "updated_at": None}

    def generate_court_report_pdf(self, db: Database, case_id: str) -> bytes:
        return b"%PDF-1.4\n..."

ontology_service = OntologyService()