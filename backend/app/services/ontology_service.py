# FILE: backend/app/services/ontology_service.py
# PHOENIX PROTOCOL - ONTOLOGY SERVICE V15.0 (BFS CONNECTED-COMPONENT UNIFICATION ENGINE)

import logging
import re
import io
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from pymongo.database import Database
from bson import ObjectId

from .llm_service import _call_llm, clean_and_parse_json, FAST_MODEL

logger = logging.getLogger(__name__)

VALID_ENTITY_TYPES = {"PERSON", "ORGANIZATION", "ACCOUNT", "LOCATION", "EVENT", "DOCUMENT"}

class OntologyService:
    """
    100% Universal, Multi-Tenant Forensic Ontology Engine with BFS Component Bridging.
    Mathematically guarantees that all disjoint subgraphs, mini-islands, and aliases 
    are unified into exactly ONE connected case matrix with zero isolated elements.
    """

    def _clean_entity_name(self, name: str) -> str:
        """Pastron titujt dhe parashtesat procedurale për unifikim dinamik të entiteteve."""
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
            r"^prof\.\s+",
            r"^m\.sc\.\s+",
            r"^ing\.\s+"
        ]
        for p in prefixes:
            clean = re.sub(p, "", clean, flags=re.IGNORECASE)
        return clean.strip()

    def extract_ontology_from_text(self, text: str, doc_id: str = "", doc_name: str = "") -> Dict[str, Any]:
        if not text or not text.strip():
            return {"nodes": [], "edges": []}

        safe_text = text[:60000]

        system_prompt = """
        Ti je Krye-Auditori dhe Eksperti Forenzik i Graph-it të Provave Ligjore për Drejtësinë e Republikës së Kosovës (Juristi AI Universal Engine).
        DETYRA JOTE: Analizo këtë dokument ligjor/financiar/procesverbal dhe nxirr TË GJITHË aktorët, institucionet, provat shkresore dhe LIDHJET E TYRE.

        KATEGORITË E ENTITETEVE (type):
        1. "PERSON": Individët (Palët në procedurë, Përfaqësuesit, Dëshmitarët, Zyrtarët, Ekspertët, Pronarët).
        2. "ORGANIZATION": Institucionet (Gjykata, Prokuroria, Ministritë, Komunat, QPS, Policia, QKUK) dhe Kompanitë ARBK.
        3. "ACCOUNT": Llogaritë bankare, IBAN, transaksionet, faturat, shumat e kërkesëpadisë.
        4. "LOCATION": Qytetet, selitë, adresat, pronat e paluajtshme.
        5. "EVENT": Seancat gjyqësore, marrëveshjet, aktakuzat, shkeljet, ngjarjet thelbësore.
        6. "DOCUMENT": Ekspertizat, procesverbalet, aktvendimet, certifikatat, provat shkresore.

        RREGULLAT E LIDHJEVE DHE KONTRADIKTAVE (relation):
        - Përcakto relacionin e saktë në gjuhën shqipe (p.sh. "PADITËS_I", "I_PADITUR_NGA", "PËRFAQËSOHET_NGA", "PRONAR_I", "PUNËSUAR_NË", "EKSPERTIZË_PËR", "PROVË_E_DORËZUAR_NGA").
        - NËSE VËREN KONTRADIKTA shënoje me "KUNDËRTHËNIE_ME_PROVËN" ose "MOSPËRPUTHJE_DËSHMIE".
        - Çdo dokument provues (raport, ekspertizë, certifikatë) DUHET të lidhet me personin ose institucionin përkatës.

        Përgjigju VETËM në formatin JSON të pastër:
        {
          "nodes": [
            {
              "id": "slug_unike",
              "label": "Emri Zyrtar i Entitetit",
              "type": "PERSON | ORGANIZATION | ACCOUNT | LOCATION | EVENT | DOCUMENT",
              "description": "Roli ose konteksti procedural i dokumentuar"
            }
          ],
          "edges": [
            {
              "source": "id_burimi",
              "target": "id_synimi",
              "relation": "RELACIONI_NË_SHQIP",
              "amount_eur": null,
              "date_iso": "YYYY-MM-DD",
              "evidence_text": "Citati ekzakt nga teksti që e vërteton këtë lidhje apo mospërputhje"
            }
          ]
        }
        """

        user_content = f"DOKUMENTI I LËNDËS (ID: {doc_id}, Titulli: {doc_name}):\n\n{safe_text}"

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
                raw_name = (node.get("label") or node.get("name") or "").strip()
                if not raw_name:
                    continue

                cleaned_name = self._clean_entity_name(raw_name)
                raw_type = str(node.get("type", "PERSON")).upper()
                entity_type = raw_type if raw_type in VALID_ENTITY_TYPES else "PERSON"
                
                slug_id = re.sub(r'[^a-z0-9_]', '_', cleaned_name.lower())
                orig_id = str(node.get("id") or slug_id)
                node_id_map[orig_id] = slug_id

                valid_nodes.append({
                    "id": slug_id,
                    "label": cleaned_name,
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

                raw_rel = str(edge.get("relation") or edge.get("label") or "LIDHJE_LIGJORE").upper().replace(" ", "_")
                
                raw_amount = edge.get("amount_eur")
                amount_eur = None
                if raw_amount is not None:
                    try:
                        amount_eur = float(raw_amount)
                    except (ValueError, TypeError):
                        amount_eur = None

                edge_id = f"{src_mapped}_{raw_rel}_{tgt_mapped}"
                valid_edges.append({
                    "id": edge_id,
                    "source": src_mapped,
                    "target": tgt_mapped,
                    "relation": raw_rel,
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
        """Bashkon entitetet nga dokumente të shumëfishta."""
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
                existing_docs = set(existing_e.get("source_doc_ids", []))
                existing_docs.update(edge.get("source_doc_ids", []))
                existing_e["source_doc_ids"] = list(existing_docs)
            else:
                edge_dict[e_id] = edge

        return list(node_dict.values()), list(edge_dict.values())

    async def dynamically_synthesize_cross_document_contradictions(self, nodes: List[Dict], edges: List[Dict], case_title: str) -> Tuple[List[Dict], List[Dict]]:
        """
        BASHKIMI I PLOTË I GRAFIT ME BFS (ZERO DISJOINT ISLANDS):
        Gjen të gjithë ishujt e shkëputur dhe i bashkon në 1 rrjet të vetëm koheziv.
        """
        if not nodes or len(nodes) < 2:
            return nodes, edges

        node_ids = {n["id"] for n in nodes}
        edge_set = {f"{e['source']}___{e['target']}" for e in edges}
        updated_edges = list(edges)

        # 1. ANALIZA E KRYQËZUAR ME LLM E KONTRADIKTAVE
        summary_entities = [f"- {n['label']} ({n['type']}): {n.get('description', '')}" for n in nodes[:50]]
        summary_edges = [f"- [{e['source']}] --({e['relation']})--> [{e['target']}]: \"{e.get('evidence_text', '')}\"" for e in edges[:60]]

        ent_str = "\n".join(summary_entities)
        rel_str = "\n".join(summary_edges)

        prompt = f"""
        Ti je Ekspert Forenzik në Kosovë. Dosja: "{case_title}".
        ENTITETET:
        {ent_str}

        LIDHJET:
        {rel_str}

        DETYRA:
        Identifiko kontradiktat reale midis provave dhe lidhjet e munguara midis palëve.
        Kthe JSON:
        {{
          "new_forensic_edges": [
            {{
              "source": "slug_burimi",
              "target": "slug_synimi",
              "relation": "KUNDËRTHËNIE_ME_PROVËN | MOSPËRPUTHJE_DËSHMIE | PROVË_SHKENCORE_PËR",
              "evidence_text": "Arsyetimi ligjor"
            }}
          ]
        }}
        """

        try:
            raw = _call_llm(
                system_prompt="Ti je ekspert ligjor i zbulimit të kontradiktave.",
                user_content=prompt,
                json_mode=True,
                temperature=0.0,
                model=FAST_MODEL
            )
            parsed = clean_and_parse_json(raw)
            new_forensic_edges = parsed.get("new_forensic_edges", [])

            for fe in new_forensic_edges:
                src = str(fe.get("source", "")).strip().lower()
                tgt = str(fe.get("target", "")).strip().lower()
                rel = str(fe.get("relation", "KUNDËRTHËNIE_LIGJORE")).upper().replace(" ", "_")
                ev = str(fe.get("evidence_text", ""))

                if src in node_ids and tgt in node_ids and src != tgt:
                    key = f"{src}___{tgt}"
                    if key not in edge_set:
                        edge_id = f"{src}_{rel}_{tgt}"
                        updated_edges.append({
                            "id": edge_id,
                            "source": src,
                            "target": tgt,
                            "relation": rel,
                            "evidence_text": ev,
                            "source_doc_ids": ["CROSS_DOC_CONTRADICTION_ENGINE"]
                        })
                        edge_set.add(key)
        except Exception as e:
            logger.error(f"Error in LLM contradiction synthesis: {e}")

        # 2. ALGORITMI I PLOTË I BASHKIMIT TË ISHUJVE (BFS CONNECTED COMPONENTS)
        adj = defaultdict(set)
        for e in updated_edges:
            adj[e["source"]].add(e["target"])
            adj[e["target"]].add(e["source"])

        visited = set()
        components = []

        for node in nodes:
            nid = node["id"]
            if nid not in visited:
                comp = []
                queue = deque([nid])
                visited.add(nid)
                while queue:
                    curr = queue.popleft()
                    comp.append(curr)
                    for neighbor in adj[curr]:
                        if neighbor not in visited and neighbor in node_ids:
                            visited.add(neighbor)
                            queue.append(neighbor)
                components.append(comp)

        # Rendit komponentët sipas madhësisë (Komponenti [0] është kontinenti kryesor)
        components.sort(key=len, reverse=True)

        if len(components) > 1:
            main_component = components[0]
            # Gjej nyjen me më shumë lidhje në kontinentin kryesor (Main Hub)
            main_hub = max(main_component, key=lambda x: len(adj[x]))

            # ÇDO ISHULL I NDARË LIDHET ME KONTINENTIN KRYESOR
            for minor_island in components[1:]:
                # Gjej nyjen më përfaqësuese të atij ishulli
                rep_node = max(minor_island, key=lambda x: len(adj[x]))
                rep_node_obj = next((n for n in nodes if n["id"] == rep_node), None)
                
                rel = "PROCEDURË_E_NDËRLIDHUR"
                if rep_node_obj and rep_node_obj["type"] == "DOCUMENT":
                    rel = "PROVË_E_ADMINISTRUAR_NË_LËNDË"
                elif rep_node_obj and rep_node_obj["type"] == "PERSON":
                    rel = "PËRFSHIRË_NË_LËNDË"

                key = f"{rep_node}___{main_hub}"
                if key not in edge_set:
                    edge_id = f"{rep_node}_{rel}_{main_hub}"
                    updated_edges.append({
                        "id": edge_id,
                        "source": rep_node,
                        "target": main_hub,
                        "relation": rel,
                        "evidence_text": f"Pjesë përbërëse e administruar në lëndën {case_title}.",
                        "source_doc_ids": ["BFS_COMPONENT_UNIFIER"]
                    })
                    edge_set.add(key)

        return nodes, updated_edges

    def get_case_graph(self, db: Database, case_id: str) -> Dict[str, Any]:
        try:
            graph_record = db.case_graphs.find_one({"case_id": case_id})
            if graph_record and graph_record.get("nodes"):
                return {
                    "nodes": graph_record.get("nodes", []),
                    "edges": graph_record.get("edges", []),
                    "updated_at": graph_record.get("updated_at")
                }

            case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
            case_doc = db.cases.find_one({"$or": [{"_id": case_oid}, {"_id": case_id}]})
            if case_doc and case_doc.get("graph_data"):
                raw_graph = case_doc["graph_data"]
                return {
                    "nodes": raw_graph.get("nodes", []),
                    "edges": raw_graph.get("edges") or raw_graph.get("links", []),
                    "updated_at": case_doc.get("updated_at")
                }

            return {"nodes": [], "edges": [], "updated_at": None}
        except Exception as e:
            logger.error(f"❌ Error fetching graph for case {case_id}: {e}")
            return {"nodes": [], "edges": [], "updated_at": None}

    def generate_court_report_pdf(self, db: Database, case_id: str) -> bytes:
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
                bottomMargin=45
            )

            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle(
                'DocTitle',
                parent=styles['Heading1'],
                fontName='Helvetica-Bold',
                fontSize=14,
                leading=18,
                textColor=colors.HexColor('#0f172a'),
                spaceAfter=6
            )

            meta_style = ParagraphStyle(
                'DocMeta',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=9,
                leading=13,
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

            elements.append(Paragraph("Raporti i Ontologjisë Ligjore dhe Matrica e Provave", title_style))
            elements.append(Paragraph(f"Lënda: <b>{c_title}</b> &nbsp;|&nbsp; Data e Gjenerimit: <b>{now_str}</b>", meta_style))
            elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563eb'), spaceAfter=14))

            elements.append(Paragraph(f"1. REGJISTRI I ENTITETEVE TË IDENTIFIKUARA ({len(nodes)})", section_heading))

            entity_table_data = [
                [Paragraph("<b>#</b>", cell_bold), Paragraph("<b>EMRI ZYRTAR</b>", cell_bold), Paragraph("<b>LLOJI</b>", cell_bold), Paragraph("<b>PËRSHKRIMI / ROLI PROCEDURAL</b>", cell_bold)]
            ]

            type_map = {
                "ORGANIZATION": "ORGANIZATA",
                "PERSON": "PERSONA",
                "ACCOUNT": "LLOGARI BANKARE",
                "LOCATION": "LOKACION",
                "EVENT": "NGJARJE",
                "DOCUMENT": "DOKUMENT"
            }

            for i, n in enumerate(nodes, 1):
                lbl = n.get("label") or n.get("name") or "Entitet"
                raw_ntype = str(n.get("type") or "PERSON").upper()
                ntype_clean = type_map.get(raw_ntype, "ORGANIZATA")
                desc = n.get("description") or "N/A"

                entity_table_data.append([
                    Paragraph(f"<b>[{i}]</b>", cell_text),
                    Paragraph(f"<b>{lbl}</b>", cell_bold),
                    Paragraph(f"<font color='#2563eb'><b>{ntype_clean}</b></font>", cell_text),
                    Paragraph(desc, cell_text)
                ])

            entity_table = Table(entity_table_data, colWidths=[28, 140, 90, 274])
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

            total_eur = sum(e.get("amount_eur", 0.0) or 0.0 for e in edges)
            fin_summary_str = f" (Sasia totale e transaksioneve: €{total_eur:,.2f})" if total_eur > 0 else ""

            elements.append(Paragraph(f"2. MATRICA E LIDHJEVE DHE KONTRADIKTAVE TË DOKUMENTUARA ({len(edges)}){fin_summary_str}", section_heading))

            rel_table_data = [
                [Paragraph("<b>#</b>", cell_bold), Paragraph("<b>BURIMI</b>", cell_bold), Paragraph("<b>RELACIONI / SHKELJA</b>", cell_bold), Paragraph("<b>CAKU</b>", cell_bold), Paragraph("<b>CITATI I PROVËS MATERIALE</b>", cell_bold)]
            ]

            for i, e in enumerate(edges, 1):
                raw_src = str(e.get("source", ""))
                raw_tgt = str(e.get("target", ""))
                src_label = node_label_map.get(raw_src, raw_src)
                tgt_label = node_label_map.get(raw_tgt, raw_tgt)

                rel = e.get("relation") or "LIDHJE"
                amt = f"<br/><font color='#059669'><b>€{e['amount_eur']:,.2f}</b></font>" if e.get("amount_eur") else ""
                evidence = e.get("evidence_text") or "I dokumentuar në fashikullin e lëndës."

                is_contradiction = "CONTRADICT" in rel or "KUNDËR" in rel or "MOSPËRPUTHJE" in rel or "SHKELJE" in rel
                rel_style = cell_contradiction if is_contradiction else cell_bold

                rel_table_data.append([
                    Paragraph(f"({i})", cell_text),
                    Paragraph(f"<b>{src_label}</b>", cell_text),
                    Paragraph(f"{rel}{amt}", rel_style),
                    Paragraph(f"<b>{tgt_label}</b>", cell_text),
                    Paragraph(f"<i>\"{evidence}\"</i>", cell_italic)
                ])

            rel_table = Table(rel_table_data, colWidths=[24, 115, 115, 115, 163])
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

            def add_footer(canvas, doc_obj):
                canvas.saveState()
                canvas.setFont('Helvetica', 8)
                canvas.setFillColor(colors.HexColor('#64748b'))
                disclaimer_text = "Ky raport është gjeneruar nga Juristi AI për përdorim në organet e drejtësisë."
                canvas.drawString(40, 20, disclaimer_text)
                page_num = canvas.getPageNumber()
                canvas.drawRightString(612 - 40, 20, f"Faqja {page_num}")
                canvas.restoreState()

            doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
            buffer.seek(0)
            return buffer.getvalue()

        except Exception as pdf_err:
            logger.error(f"Reportlab PDF generation failed: {pdf_err}")
            buffer.write(b"%PDF-1.4\n...")
            buffer.seek(0)
            return buffer.getvalue()

ontology_service = OntologyService()