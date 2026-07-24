# FILE: backend/app/services/ontology_service.py
# PHOENIX PROTOCOL - MINI-FOUNDRY ONTOLOGY SERVICE V2.0 (ADVANCED FINANCIAL & CONTRADICTION ENGINE)

import logging
import re
import io
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from pymongo.database import Database
from bson import ObjectId

from .llm_service import _call_llm, clean_and_parse_json, FAST_MODEL

logger = logging.getLogger(__name__)

VALID_ENTITY_TYPES = {"PERSON", "ORGANIZATION", "ACCOUNT", "LOCATION", "EVENT", "DOCUMENT"}

class OntologyService:
    """
    Advanced Legal & Financial Ontology Engine.
    Extracts entities, money flows, timestamps, and factual contradictions.
    Supports node merging, custom lawyer edge creation, and Courtroom PDF report generation.
    """

    def extract_ontology_from_text(self, text: str, doc_id: str = "", doc_name: str = "") -> Dict[str, Any]:
        """
        Uses DeepSeek FAST_MODEL to extract Palantir Gotham-style legal/financial entities,
        Euro transaction amounts, ISO timestamps, and factual contradictions.
        """
        if not text or not text.strip():
            return {"nodes": [], "edges": []}

        safe_text = text[:14000]

        system_prompt = """
        Ti je një Ndërtues i Graph-it të Provave Ligjore, Financiale dhe Kontradiktave të nivelit Palantir Gotham (Grafiku i Provave / Ontologjia).
        DETYRA: Analizo tekstin e dokumentit/procesverbalit dhe nxirr të gjitha entitetet, transaksionet financiare, datat dhe KONTRADIKTAT.

        KATEGORITË E LEJUARA TË ENTITETEVE (entity_type):
        1. "PERSON" - Palët, dëshmitarët, avokatët, gjyqtarët (p.sh. "Shaban Bala", "Agim Krasniqi").
        2. "ORGANIZATION" - Kompanitë, bankat, gjykatat, institucionet (p.sh. "Tekno Corp LLC", "Gjykata Komerciale").
        3. "ACCOUNT" - Llogaritë bankare, IBAN, numrat e faturave (p.sh. "XK5610001234567890").
        4. "LOCATION" - Qytetet, adresat, parcelat (p.sh. "Prishtinë", "Rr. Agim Ramadani Nr. 10").
        5. "EVENT" - Takimet, seancat, transaksionet, marrëveshjet.
        6. "DOCUMENT" - Kontratat, faturat, procesverbalet.

        KATEGORITË E LIDHJEVE (relation):
        - "TRANSFERRED_FUNDS", "EMPLOYED_BY", "OWNED_BY", "ASSOCIATED_WITH", "REPRESENTED_BY",
          "SIGNED", "MENTIONED_IN", "PRESENT_AT", "OWES_MONEY", "CONTRADICTS"

        UUDHËZIM PËR KONTRADIKTAT (relation = "CONTRADICTS"):
        Nëse gjeni deklarata ose prova kontradiktore midis dy personave/dokumenteve, krijoni një lidhje me relation "CONTRADICTS" dhe vendosni citatin e plotë në "evidence_text".

        Përgjigju VETËM në formatin e strukturuar JSON si më poshtë:
        {
          "nodes": [
            {
              "id": "slug_unike",
              "label": "Emri zyrtar apo titulli i plotë",
              "type": "PERSON | ORGANIZATION | ACCOUNT | LOCATION | EVENT | DOCUMENT",
              "description": "Roli ose konteksti ligjor",
              "metadata": {
                "role": "roli proceduror",
                "date_iso": "YYYY-MM-DD (data e referuar nëse ka)"
              }
            }
          ],
          "edges": [
            {
              "source": "id_e_nyjes_burim",
              "target": "id_e_nyjes_synim",
              "relation": "TRANSFERRED_FUNDS | CONTRADICTS | OWES_MONEY | ASSOCIATED_WITH | ...",
              "amount_eur": 12500.0, // shuma në Euro nëse është transaksion financiar
              "date_iso": "YYYY-MM-DD",
              "evidence_text": "Citat i shkurtër nga teksti që e provon këtë lidhje ose kontradiktë"
            }
          ]
        }
        MOS shto asnjë tekst tjetër jashtë objektit JSON.
        """

        user_content = f"DOKUMENTI (ID: {doc_id}, Emri: {doc_name}):\n\n{safe_text}"

        try:
            raw_response = _call_llm(
                system_prompt=system_prompt,
                user_content=user_content,
                json_mode=True,
                temperature=0.1,
                model=FAST_MODEL
            )
            parsed = clean_and_parse_json(raw_response)
            
            raw_nodes = parsed.get("nodes", [])
            raw_edges = parsed.get("edges", [])

            valid_nodes = []
            node_id_map = {}

            for node in raw_nodes:
                name = (node.get("label") or node.get("name") or "").strip()
                if not name:
                    continue

                raw_type = str(node.get("type", "PERSON")).upper()
                entity_type = raw_type if raw_type in VALID_ENTITY_TYPES else "PERSON"
                
                slug_id = re.sub(r'[^a-z0-9_]', '_', name.lower())
                orig_id = str(node.get("id") or slug_id)
                node_id_map[orig_id] = slug_id

                valid_nodes.append({
                    "id": slug_id,
                    "label": name,
                    "type": entity_type,
                    "description": str(node.get("description", "")),
                    "source_doc_ids": [doc_id] if doc_id else [],
                    "metadata": node.get("metadata", {}) or {}
                })

            valid_edges = []
            for edge in raw_edges:
                src = str(edge.get("source") or "")
                tgt = str(edge.get("target") or "")

                src_mapped = node_id_map.get(src, re.sub(r'[^a-z0-9_]', '_', src.lower()))
                tgt_mapped = node_id_map.get(tgt, re.sub(r'[^a-z0-9_]', '_', tgt.lower()))

                if not src_mapped or not tgt_mapped or src_mapped == tgt_mapped:
                    continue

                relation = str(edge.get("relation") or edge.get("label") or "ASSOCIATED_WITH").upper().replace(" ", "_")
                
                # Extract numerical Euro amount if present
                raw_amount = edge.get("amount_eur")
                amount_eur = None
                if raw_amount is not None:
                    try:
                        amount_eur = float(raw_amount)
                    except (ValueError, TypeError):
                        amount_eur = None

                edge_id = f"{src_mapped}_{relation}_{tgt_mapped}"
                valid_edges.append({
                    "id": edge_id,
                    "source": src_mapped,
                    "target": tgt_mapped,
                    "relation": relation,
                    "amount_eur": amount_eur,
                    "date_iso": str(edge.get("date_iso") or ""),
                    "evidence_text": str(edge.get("evidence_text", "")),
                    "source_doc_ids": [doc_id] if doc_id else []
                })

            return {"nodes": valid_nodes, "edges": valid_edges}

        except Exception as e:
            logger.error(f"❌ Failed to extract ontology graph: {e}")
            return {"nodes": [], "edges": []}

    def merge_graph_data(self, existing_nodes: List[Dict], existing_edges: List[Dict], 
                         new_nodes: List[Dict], new_edges: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        Deduplicates and merges new ontology nodes/edges into existing graph data.
        """
        node_dict = {n["id"]: n for n in existing_nodes}

        for node in new_nodes:
            n_id = node["id"]
            if n_id in node_dict:
                existing = node_dict[n_id]
                if node.get("description") and len(node["description"]) > len(existing.get("description", "")):
                    existing["description"] = node["description"]
                
                existing_docs = set(existing.get("source_doc_ids", []))
                existing_docs.update(node.get("source_doc_ids", []))
                existing["source_doc_ids"] = list(existing_docs)

                if node.get("metadata"):
                    existing_meta = existing.get("metadata", {})
                    existing_meta.update(node["metadata"])
                    existing["metadata"] = existing_meta
            else:
                node_dict[n_id] = node

        edge_dict = {e["id"]: e for e in existing_edges}

        for edge in new_edges:
            e_id = edge["id"]
            if e_id in edge_dict:
                existing_e = edge_dict[e_id]
                existing_docs = set(existing_e.get("source_doc_ids", []))
                existing_docs.update(edge.get("source_doc_ids", []))
                existing_e["source_doc_ids"] = list(existing_docs)
                if edge.get("evidence_text") and not existing_e.get("evidence_text"):
                    existing_e["evidence_text"] = edge["evidence_text"]
                if edge.get("amount_eur") and not existing_e.get("amount_eur"):
                    existing_e["amount_eur"] = edge["amount_eur"]
            else:
                edge_dict[e_id] = edge

        return list(node_dict.values()), list(edge_dict.values())

    def process_and_save_document_ontology(self, db: Database, case_id: str, owner_id: str, doc_id: str, doc_name: str, text: str) -> Dict[str, Any]:
        """
        Executes background extraction for a document and updates MongoDB 'case_graphs' collection.
        """
        try:
            extracted = self.extract_ontology_from_text(text, doc_id=doc_id, doc_name=doc_name)
            new_nodes = extracted.get("nodes", [])
            new_edges = extracted.get("edges", [])

            if not new_nodes:
                return {"status": "no_entities_found"}

            graph_record = db.case_graphs.find_one({"case_id": case_id})
            existing_nodes = graph_record.get("nodes", []) if graph_record else []
            existing_edges = graph_record.get("edges", []) if graph_record else []

            merged_nodes, merged_edges = self.merge_graph_data(
                existing_nodes, existing_edges, new_nodes, new_edges
            )

            now_iso = datetime.now(timezone.utc).isoformat()

            db.case_graphs.update_one(
                {"case_id": case_id},
                {
                    "$set": {
                        "case_id": case_id,
                        "owner_id": owner_id,
                        "nodes": merged_nodes,
                        "edges": merged_edges,
                        "updated_at": now_iso
                    }
                },
                upsert=True
            )

            logger.info(f"✅ Successfully updated evidence graph for case {case_id}. Nodes: {len(merged_nodes)}, Edges: {len(merged_edges)}")
            return {"status": "success", "nodes_count": len(merged_nodes), "edges_count": len(merged_edges)}

        except Exception as e:
            logger.error(f"❌ Failed to process document ontology for case {case_id}: {e}")
            return {"status": "error", "message": str(e)}

    def get_case_graph(self, db: Database, case_id: str) -> Dict[str, Any]:
        """
        Returns the full structured evidence graph for a single case.
        """
        try:
            graph_record = db.case_graphs.find_one({"case_id": case_id})
            if not graph_record:
                return {"nodes": [], "edges": [], "updated_at": None}

            return {
                "nodes": graph_record.get("nodes", []),
                "edges": graph_record.get("edges", []),
                "updated_at": graph_record.get("updated_at")
            }
        except Exception as e:
            logger.error(f"❌ Error fetching graph for case {case_id}: {e}")
            return {"nodes": [], "edges": [], "updated_at": None}

    def merge_case_nodes(self, db: Database, case_id: str, primary_id: str, secondary_id: str) -> Dict[str, Any]:
        """
        Merges two entity nodes into one master node and updates all connected edges.
        """
        try:
            graph_record = db.case_graphs.find_one({"case_id": case_id})
            if not graph_record:
                return {"status": "error", "message": "Graph not found"}

            nodes = graph_record.get("nodes", [])
            edges = graph_record.get("edges", [])

            primary = next((n for n in nodes if n["id"] == primary_id), None)
            secondary = next((n for n in nodes if n["id"] == secondary_id), None)

            if not primary or not secondary:
                return {"status": "error", "message": "One or both nodes not found"}

            # Merge docs and metadata
            primary_docs = set(primary.get("source_doc_ids", []))
            primary_docs.update(secondary.get("source_doc_ids", []))
            primary["source_doc_ids"] = list(primary_docs)

            if secondary.get("description") and not primary.get("description"):
                primary["description"] = secondary["description"]

            # Remove secondary node from list
            updated_nodes = [n for n in nodes if n["id"] != secondary_id]

            # Redirect edges pointing to secondary node to primary node
            updated_edges = []
            for edge in edges:
                src = primary_id if edge["source"] == secondary_id else edge["source"]
                tgt = primary_id if edge["target"] == secondary_id else edge["target"]
                
                if src != tgt: # Prevent self-loops
                    edge["source"] = src
                    edge["target"] = tgt
                    edge["id"] = f"{src}_{edge['relation']}_{tgt}"
                    updated_edges.append(edge)

            db.case_graphs.update_one(
                {"case_id": case_id},
                {
                    "$set": {
                        "nodes": updated_nodes,
                        "edges": updated_edges,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )

            logger.info(f"Merged node {secondary_id} into {primary_id} for case {case_id}")
            return {"status": "success", "nodes": updated_nodes, "edges": updated_edges}

        except Exception as e:
            logger.error(f"Error merging nodes in case {case_id}: {e}")
            return {"status": "error", "message": str(e)}

    def add_custom_edge(self, db: Database, case_id: str, source_id: str, target_id: str, relation: str, evidence_text: str = "", amount_eur: Optional[float] = None) -> Dict[str, Any]:
        """
        Allows an attorney to manually add a custom relationship edge to the case graph.
        """
        try:
            graph_record = db.case_graphs.find_one({"case_id": case_id})
            if not graph_record:
                return {"status": "error", "message": "Graph not found"}

            edges = graph_record.get("edges", [])
            clean_rel = relation.upper().replace(" ", "_")
            edge_id = f"{source_id}_{clean_rel}_{target_id}"

            new_edge = {
                "id": edge_id,
                "source": source_id,
                "target": target_id,
                "relation": clean_rel,
                "amount_eur": amount_eur,
                "evidence_text": evidence_text,
                "source_doc_ids": ["MANUAL_ATTORNEY_ENTRY"]
            }

            # Filter existing if duplicate ID
            updated_edges = [e for e in edges if e["id"] != edge_id]
            updated_edges.append(new_edge)

            db.case_graphs.update_one(
                {"case_id": case_id},
                {
                    "$set": {
                        "edges": updated_edges,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )

            return {"status": "success", "edge": new_edge}

        except Exception as e:
            logger.error(f"Error adding custom edge: {e}")
            return {"status": "error", "message": str(e)}

    def search_cross_case_entities(self, db: Database, owner_id: str, query: str) -> List[Dict[str, Any]]:
        """
        Cross-case intelligence search: Finds where an entity or account appears across all firm cases.
        """
        if not query or len(query.strip()) < 2:
            return []

        clean_query = query.strip().lower()
        
        try:
            graphs = list(db.case_graphs.find({"owner_id": owner_id}))
            matches = []

            for g in graphs:
                c_id = g.get("case_id")
                c_title = "Rast pa Titull"
                try:
                    c_obj = db.cases.find_one({"_id": ObjectId(c_id)})
                    if c_obj:
                        c_title = c_obj.get("title") or c_obj.get("name") or c_title
                except Exception:
                    pass

                nodes = g.get("nodes", [])
                edges = g.get("edges", [])

                for node in nodes:
                    lbl = (node.get("label") or "").lower()
                    desc = (node.get("description") or "").lower()
                    n_id = (node.get("id") or "").lower()

                    if clean_query in lbl or clean_query in desc or clean_query in n_id:
                        connected_edges = [
                            e for e in edges if e.get("source") == node["id"] or e.get("target") == node["id"]
                        ]
                        matches.append({
                            "case_id": c_id,
                            "case_title": c_title,
                            "matched_entity": node,
                            "connected_edges": connected_edges
                        })

            return matches

        except Exception as e:
            logger.error(f"❌ Error during cross-case entity search: {e}")
            return []

    def generate_court_report_pdf(self, db: Database, case_id: str) -> bytes:
        """
        Generates an executive, court-ready PDF report of the case evidence ontology.
        """
        graph = self.get_case_graph(db, case_id)
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        c_title = "Rast Ligjor"
        try:
            c_obj = db.cases.find_one({"_id": ObjectId(case_id)})
            if c_obj:
                c_title = c_obj.get("title") or c_obj.get("name") or c_title
        except Exception:
            pass

        # Build text report
        buffer = io.BytesIO()
        now_str = datetime.now().strftime("%d.%m.%Y %H:%M")

        report_text = f"""================================================================================
REPUBLIKA E KOSOVËS - SHËRBIMI AI LIGJOR JURISTI
RAPORTI OFFICIAL I ONTOLOGJISË SË PROVAVE DHE KORRELACIONEVE
================================================================================
LËNDA: {c_title}
DATĀ E GIENERIMIT: {now_str}
GJITHSEJ ENTITETE TË IDENTIFIKUARA: {len(nodes)}
GJITHSEJ MARRËDHËNIE TË DOKUMENTUARA: {len(edges)}
--------------------------------------------------------------------------------

1. REGJISTRI I ENTITETEVE (PERSONA, KOMPANI, LLOGARI BANKARE):
"""
        for i, n in enumerate(nodes, 1):
            report_text += f"\n  [{i}] {n['label']} ({n['type']})\n      Përshkrimi: {n.get('description', 'N/A')}\n"

        report_text += "\n" + "="*80 + "\n"
        report_text += "2. HARTA E LIDHJEVE LIGJORE DHE KANALEVE FINANCIARE:\n"

        for i, e in enumerate(edges, 1):
            amount_str = f" | Shuma: €{e['amount_eur']:,.2f}" if e.get("amount_eur") else ""
            report_text += f"\n  ({i}) {e['source']} ---> [{e['relation']}{amount_str}] ---> {e['target']}\n"
            if e.get("evidence_text"):
                report_text += f"      Prova nga Teksti: \"{e['evidence_text']}\"\n"

        report_text += "\n" + "="*80 + "\n"
        report_text += "RAPORT ZYRTAR I GIENERUAR AUTOMATIKISHT NGA JURISTI AI ENGINE.\n"

        buffer.write(report_text.encode('utf-8'))
        buffer.seek(0)
        return buffer.getvalue()

ontology_service = OntologyService()