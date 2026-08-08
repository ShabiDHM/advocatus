# FILE: backend/app/services/ontology_service.py
# PHOENIX PROTOCOL - MINI-FOUNDRY ONTOLOGY SERVICE V7.0 (UPDATED COURT REPORT HEADER)

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
        if not text or not text.strip():
            return {"nodes": [], "edges": []}

        safe_text = text[:14000]

        system_prompt = """
        Ti je një Ndërtues i Graph-it të Provave Ligjore, Financiale dhe Kontradiktave të nivelit Palantir Gotham (Grafiku i Provave / Ontologjia).
        DETYRA: Analizo tekstin e dokumentit/procesverbalit dhe nxirr të gjitha entitetet, transaksionet financiare, datat dhe KONTRADIKTAT.

        KATEGORITË E LEJUARA TË ENTITETEVE (entity_type):
        1. "PERSON" - Palët, dëshmitarët, avokatët, gjyqtarët.
        2. "ORGANIZATION" - Kompanitë, bankat, gjykatat, institucionet.
        3. "ACCOUNT" - Llogaritë bankare, IBAN, numrat e faturave.
        4. "LOCATION" - Qytetet, adresat, parcelat.
        5. "EVENT" - Takimet, seancat, transaksionet, marrëveshjet.
        6. "DOCUMENT" - Kontratat, faturat, procesverbalet.

        KATEGORITË E LIDHJEVE (relation):
        - "TRANSFERRED_FUNDS", "EMPLOYED_BY", "OWNED_BY", "ASSOCIATED_WITH", "REPRESENTED_BY",
          "SIGNED", "MENTIONED_IN", "PRESENT_AT", "OWES_MONEY", "CONTRADICTS"

        Përgjigju VETËM në formatin e strukturuar JSON:
        {
          "nodes": [
            {
              "id": "slug_unike",
              "label": "Emri zyrtar apo titulli i plotë",
              "type": "PERSON | ORGANIZATION | ACCOUNT | LOCATION | EVENT | DOCUMENT",
              "description": "Roli ose konteksti ligjor"
            }
          ],
          "edges": [
            {
              "source": "id_e_nyjes_burim",
              "target": "id_e_nyjes_synim",
              "relation": "TRANSFERRED_FUNDS | CONTRADICTS | OWES_MONEY | ASSOCIATED_WITH | ...",
              "amount_eur": 12500.0,
              "date_iso": "YYYY-MM-DD",
              "evidence_text": "Citat i shkurtër nga teksti që e provon këtë lidhje ose kontradiktë"
            }
          ]
        }
        """

        user_content = f"DOKUMENTI (ID: {doc_id}, Emri: {doc_name}):\n\n{safe_text}"

        try:
            raw_response = _call_llm(
                system_prompt=system_prompt,
                user_content=user_content,
                json_mode=True,
                temperature=0.0,
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
            else:
                node_dict[n_id] = node

        edge_dict = {e["id"]: e for e in existing_edges}

        for edge in new_edges:
            e_id = edge["id"]
            if e_id in edge_dict:
                existing_e = edge_dict[e_id]
                if edge.get("evidence_text") and not existing_e.get("evidence_text"):
                    existing_e["evidence_text"] = edge["evidence_text"]
            else:
                edge_dict[e_id] = edge

        return list(node_dict.values()), list(edge_dict.values())

    def process_and_save_document_ontology(self, db: Database, case_id: str, owner_id: str, doc_id: str, doc_name: str, text: str) -> Dict[str, Any]:
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

            return {"status": "success", "nodes_count": len(merged_nodes), "edges_count": len(merged_edges)}

        except Exception as e:
            logger.error(f"❌ Failed to process document ontology for case {case_id}: {e}")
            return {"status": "error", "message": str(e)}

    def get_case_graph(self, db: Database, case_id: str) -> Dict[str, Any]:
        try:
            case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
            case_doc = db.cases.find_one({"$or": [{"_id": case_oid}, {"_id": case_id}]})
            if case_doc and case_doc.get("graph_data"):
                raw_graph = case_doc["graph_data"]
                return {
                    "nodes": raw_graph.get("nodes", []),
                    "edges": raw_graph.get("edges") or raw_graph.get("links", []),
                    "updated_at": case_doc.get("updated_at")
                }

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

            updated_nodes = [n for n in nodes if n["id"] != secondary_id]
            updated_edges = []
            for edge in edges:
                src = primary_id if edge["source"] == secondary_id else edge["source"]
                tgt = primary_id if edge["target"] == secondary_id else edge["target"]
                
                if src != tgt:
                    edge["source"] = src
                    edge["target"] = tgt
                    edge["id"] = f"{src}_{edge['relation']}_{tgt}"
                    updated_edges.append(edge)

            db.case_graphs.update_one(
                {"case_id": case_id},
                {"$set": {"nodes": updated_nodes, "edges": updated_edges, "updated_at": datetime.now(timezone.utc).isoformat()}}
            )

            return {"status": "success", "nodes": updated_nodes, "edges": updated_edges}

        except Exception as e:
            logger.error(f"Error merging nodes in case {case_id}: {e}")
            return {"status": "error", "message": str(e)}

    def add_custom_edge(self, db: Database, case_id: str, source_id: str, target_id: str, relation: str, evidence_text: str = "", amount_eur: Optional[float] = None) -> Dict[str, Any]:
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

            updated_edges = [e for e in edges if e["id"] != edge_id]
            updated_edges.append(new_edge)

            db.case_graphs.update_one(
                {"case_id": case_id},
                {"$set": {"edges": updated_edges, "updated_at": datetime.now(timezone.utc).isoformat()}}
            )

            return {"status": "success", "edge": new_edge}

        except Exception as e:
            logger.error(f"Error adding custom edge: {e}")
            return {"status": "error", "message": str(e)}

    def search_cross_case_entities(self, db: Database, owner_id: str, query: str) -> List[Dict[str, Any]]:
        if not query or len(query.strip()) < 2:
            return []

        clean_query = query.strip().lower()
        try:
            graphs = list(db.case_graphs.find({"owner_id": owner_id}))
            matches = []

            for g in graphs:
                c_id = g.get("case_id")
                c_title = "Rast Ligjor"
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
                    if clean_query in lbl:
                        connected_edges = [e for e in edges if e.get("source") == node["id"] or e.get("target") == node["id"]]
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
        Generates an official courtroom PDF report with ReportLab Tables, alternating row colors,
        financial totals, and human-readable entity names.
        """
        graph = self.get_case_graph(db, case_id)
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        node_label_map = {}
        for n in nodes:
            n_id = str(n.get("id", ""))
            n_label = str(n.get("label") or n.get("name") or n_id)
            node_label_map[n_id] = n_label

        c_title = "Rast Ligjor"
        try:
            case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
            c_obj = db.cases.find_one({"$or": [{"_id": case_oid}, {"_id": case_id}]})
            if c_obj:
                c_title = c_obj.get("title") or c_obj.get("name") or c_title
        except Exception:
            pass

        buffer = io.BytesIO()
        now_str = datetime.now().strftime("%d.%m.%Y %H:%M")

        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                leftMargin=40,
                rightMargin=40,
                topMargin=40,
                bottomMargin=40
            )

            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle(
                'DocTitle',
                parent=styles['Heading1'],
                fontName='Helvetica-Bold',
                fontSize=13,
                leading=17,
                textColor=colors.HexColor('#0f172a'),
                spaceAfter=6
            )

            meta_style = ParagraphStyle(
                'DocMeta',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=9,
                leading=12,
                textColor=colors.HexColor('#475569'),
                spaceAfter=12
            )

            section_heading = ParagraphStyle(
                'SectionHeading',
                parent=styles['Heading2'],
                fontName='Helvetica-Bold',
                fontSize=11,
                leading=15,
                textColor=colors.HexColor('#0f172a'),
                spaceBefore=12,
                spaceAfter=8
            )

            cell_bold = ParagraphStyle(
                'CellBold',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=8.5,
                leading=11,
                textColor=colors.HexColor('#0f172a')
            )

            cell_text = ParagraphStyle(
                'CellText',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=8,
                leading=11,
                textColor=colors.HexColor('#334155')
            )

            cell_italic = ParagraphStyle(
                'CellItalic',
                parent=styles['Normal'],
                fontName='Helvetica-Oblique',
                fontSize=8,
                leading=11,
                textColor=colors.HexColor('#475569')
            )

            cell_contradiction = ParagraphStyle(
                'CellContradiction',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=8,
                leading=11,
                textColor=colors.HexColor('#dc2626')
            )

            elements = []

            # 1. HEADER BLOCK (UPDATED ACCORDING TO USER SPECIFICATION)
            elements.append(Paragraph("RAPORTI I ONTOLOGJISË SË PROVAVE DHE KANALEVE", title_style))
            elements.append(Paragraph(f"Lënda: <b>{c_title}</b> | Data e Gjenerimit: <b>{now_str}</b> | Id e Lëndës: <font name='Courier'>{case_id[:12]}</font>", meta_style))
            elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563eb'), spaceAfter=14))

            # 2. ENTITIES REGISTRY TABLE
            elements.append(Paragraph(f"1. REGJISTRI I ENTITETEVE TË IDENTIFIKUARA ({len(nodes)})", section_heading))

            entity_table_data = [
                [Paragraph("<b>#</b>", cell_bold), Paragraph("<b>EMRI ZYRTAR (ENTITY)</b>", cell_bold), Paragraph("<b>LLOJI</b>", cell_bold), Paragraph("<b>PËRSHKRIMI / ROLI I DOKUMENTUAR</b>", cell_bold)]
            ]

            for i, n in enumerate(nodes, 1):
                lbl = n.get("label") or n.get("name") or "Entitet"
                ntype = n.get("type") or n.get("group") or "PERSON"
                desc = n.get("description") or "N/A"

                entity_table_data.append([
                    Paragraph(f"<b>[{i}]</b>", cell_text),
                    Paragraph(f"<b>{lbl}</b>", cell_bold),
                    Paragraph(f"<font color='#2563eb'><b>{ntype}</b></font>", cell_text),
                    Paragraph(desc, cell_text)
                ])

            entity_table = Table(entity_table_data, colWidths=[24, 150, 95, 263])
            entity_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')])
            ]))
            elements.append(entity_table)
            elements.append(Spacer(1, 16))

            # 3. EVIDENCE RELATIONSHIPS & FINANCIAL MATRIX TABLE
            total_eur = sum(e.get("amount_eur", 0.0) or 0.0 for e in edges)
            fin_summary_str = f" (Sasia totale e transaksioneve: €{total_eur:,.2f})" if total_eur > 0 else ""

            elements.append(Paragraph(f"2. HARTA E LIDHJEVE LIGJORE DHE KANALEVE FINANCIARE ({len(edges)}){fin_summary_str}", section_heading))

            rel_table_data = [
                [Paragraph("<b>#</b>", cell_bold), Paragraph("<b>BURIMI (SOURCE)</b>", cell_bold), Paragraph("<b>LIDHJA / TRANSAKSIONI</b>", cell_bold), Paragraph("<b>CAKU (TARGET)</b>", cell_bold), Paragraph("<b>DËSHMIA NGA SHKRESA ORIGJINALE</b>", cell_bold)]
            ]

            for i, e in enumerate(edges, 1):
                raw_src = str(e.get("source", ""))
                raw_tgt = str(e.get("target", ""))
                src_label = node_label_map.get(raw_src, raw_src)
                tgt_label = node_label_map.get(raw_tgt, raw_tgt)

                rel = e.get("relation") or e.get("label") or "LIDHJE"
                amt = f"<br/><font color='#059669'><b>€{e['amount_eur']:,.2f}</b></font>" if e.get("amount_eur") else ""
                evidence = e.get("evidence_text") or "I dokumentuar në fashikullin e lëndës."

                is_contradiction = "CONTRADICT" in rel or "KUNDËR" in rel
                rel_style = cell_contradiction if is_contradiction else cell_bold

                rel_table_data.append([
                    Paragraph(f"({i})", cell_text),
                    Paragraph(f"<b>{src_label}</b>", cell_text),
                    Paragraph(f"{rel}{amt}", rel_style),
                    Paragraph(f"<b>{tgt_label}</b>", cell_text),
                    Paragraph(f"<i>\"{evidence}\"</i>", cell_italic)
                ])

            rel_table = Table(rel_table_data, colWidths=[20, 115, 115, 115, 167])
            rel_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')])
            ]))
            elements.append(rel_table)

            doc.build(elements)
            buffer.seek(0)
            return buffer.getvalue()

        except Exception as pdf_err:
            logger.error(f"Reportlab PDF generation failed: {pdf_err}")
            buffer.write(b"%PDF-1.4\n...")
            buffer.seek(0)
            return buffer.getvalue()

ontology_service = OntologyService()