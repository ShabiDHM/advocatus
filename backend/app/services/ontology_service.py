# FILE: backend/app/services/ontology_service.py
# PHOENIX PROTOCOL - MINI-FOUNDRY ONTOLOGY SERVICE V1.0
# Native Palantir-Style Legal & Financial Entity Graph Builder for MongoDB Atlas ('case_graphs')

import logging
import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from pymongo.database import Database
from bson import ObjectId

from .llm_service import _call_llm, clean_and_parse_json, FAST_MODEL

logger = logging.getLogger(__name__)

# Valid Palantir-style Ontology Entity Types
VALID_ENTITY_TYPES = {"PERSON", "ORGANIZATION", "ACCOUNT", "LOCATION", "EVENT", "DOCUMENT"}

class OntologyService:
    """
    Palantir-style Ontology extraction and graph builder service.
    Extracts structured Entities (Nodes) & Relationships (Edges) from legal documents,
    audio transcripts, and financial logs, storing them in MongoDB 'case_graphs'.
    """

    def extract_ontology_from_text(self, text: str, doc_id: str = "", doc_name: str = "") -> Dict[str, Any]:
        """
        Uses DeepSeek FAST_MODEL to extract structured Palantir Foundry-style entities and edges.
        """
        if not text or not text.strip():
            return {"nodes": [], "edges": []}

        # Truncate text to fit within standard prompt window safely
        safe_text = text[:12000]

        system_prompt = """
        Ti je një Ndërtues i Graph-it të Provave Ligjore dhe Financiale i nivelit Palantir Foundry (Grafiku i Provave).
        DETYRA: Analizo tekstin e dokumentit/transkriptit dhe nxirr të gjitha entitetet kryesore (Nyjet/Nodes) dhe lidhjet midis tyre (Rrethinat/Edges).

        KATEGORITË E LEJUARA TË ENTITETEVE (entity_type):
        1. "PERSON" - Palët, dëshmitarët, avokatët, gjyqtarët, zyrtarët (p.sh. "Shaban Bala", "Agim Krasniqi").
        2. "ORGANIZATION" - Kompanitë, bankat, gjykatat, institucionet (p.sh. "Tekno Corp LLC", "Gjykata Themelore").
        3. "ACCOUNT" - Llogaritë bankare, IBAN, numrat e faturave, kuletat (p.sh. "XK5610001234567890").
        4. "LOCATION" - Qytetet, adresat, parcelat kadastrale (p.sh. "Prishtinë", "Rr. Agim Ramadani Nr. 10").
        5. "EVENT" - Takimet, transaksionet, seancat gjyqësore, marrëveshjet, incidentet.
        6. "DOCUMENT" - Kontratat, faturat, vendimet, prokurat.

        KATEGORITË E LIDHJEVE (relation_type):
        - "TRANSFERRED_FUNDS", "EMPLOYED_BY", "OWNED_BY", "ASSOCIATED_WITH", "REPRESENTED_BY",
          "SIGNED", "MENTIONED_IN", "PRESENT_AT", "ISSUED_TO", "CONTRADICTS", "OWES_MONEY"

        Përgjigju VETËM në formatin e strukturuar JSON si më poshtë:
        {
          "nodes": [
            {
              "id": "id_unike_e_thjeshtuar_slug_kodi",
              "label": "Emri zyrtar ose titulli i plotë",
              "type": "PERSON | ORGANIZATION | ACCOUNT | LOCATION | EVENT | DOCUMENT",
              "description": "Përshkrim i shkurtër i rolit apo kontekstit në dokument",
              "metadata": {
                "amount": "shuma nëse ka",
                "date": "data nëse ka",
                "role": "roli ligjor nëse ka"
              }
            }
          ],
          "edges": [
            {
              "source": "id_e_nyjes_burim",
              "target": "id_e_nyjes_synim",
              "relation": "LIDHJA_ME_SHKRONJA_TË_MËDHA",
              "evidence_text": "Citat i shkurtër nga teksti që e vërteton këtë lidhje"
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

            # Standardize and clean nodes
            valid_nodes = []
            node_id_map = {}

            for node in raw_nodes:
                name = (node.get("label") or node.get("name") or "").strip()
                if not name:
                    continue

                raw_type = str(node.get("type", "PERSON")).upper()
                entity_type = raw_type if raw_type in VALID_ENTITY_TYPES else "PERSON"
                
                # Slugify node ID for clean graph operations
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

            # Standardize and clean edges
            valid_edges = []
            for edge in raw_edges:
                src = str(edge.get("source") or "")
                tgt = str(edge.get("target") or "")

                # Map to slugified IDs if applicable
                src_mapped = node_id_map.get(src, re.sub(r'[^a-z0-9_]', '_', src.lower()))
                tgt_mapped = node_id_map.get(tgt, re.sub(r'[^a-z0-9_]', '_', tgt.lower()))

                if not src_mapped or not tgt_mapped or src_mapped == tgt_mapped:
                    continue

                relation = str(edge.get("relation") or edge.get("label") or "ASSOCIATED_WITH").upper().replace(" ", "_")
                
                edge_id = f"{src_mapped}_{relation}_{tgt_mapped}"
                valid_edges.append({
                    "id": edge_id,
                    "source": src_mapped,
                    "target": tgt_mapped,
                    "relation": relation,
                    "evidence_text": str(edge.get("evidence_text", "")),
                    "source_doc_ids": [doc_id] if doc_id else []
                })

            return {"nodes": valid_nodes, "edges": valid_edges}

        except Exception as e:
            logger.error(f"❌ Failed to extract ontology graph from text: {e}")
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
                # Merge description and source docs
                existing = node_dict[n_id]
                if node.get("description") and len(node["description"]) > len(existing.get("description", "")):
                    existing["description"] = node["description"]
                
                # Deduplicate source docs
                existing_docs = set(existing.get("source_doc_ids", []))
                existing_docs.update(node.get("source_doc_ids", []))
                existing["source_doc_ids"] = list(existing_docs)

                # Merge metadata
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
                logger.info(f"No new ontology entities found for doc {doc_id} in case {case_id}")
                return {"status": "no_entities_found"}

            # Fetch existing case graph record or prepare new
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

            logger.info(f"✅ Successfully updated evidence graph for case {case_id}. Total Nodes: {len(merged_nodes)}, Edges: {len(merged_edges)}")
            return {
                "status": "success",
                "nodes_count": len(merged_nodes),
                "edges_count": len(merged_edges)
            }

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

    def search_cross_case_entities(self, db: Database, owner_id: str, query: str) -> List[Dict[str, Any]]:
        """
        Cross-case intelligence search: Finds where an entity or account appears across all firm cases.
        """
        if not query or len(query.strip()) < 2:
            return []

        clean_query = query.strip().lower()
        
        try:
            # Query all graphs owned by user/firm
            graphs = list(db.case_graphs.find({"owner_id": owner_id}))
            matches = []

            for g in graphs:
                c_id = g.get("case_id")
                
                # Fetch case details for display name
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
                        # Find connected edges for this matched node
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

ontology_service = OntologyService()