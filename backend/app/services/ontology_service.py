# FILE: backend/app/services/ontology_service.py
# PHOENIX PROTOCOL - ONTOLOGY SERVICE V10.0 (KOSOVO LEGAL FORENSIC DEEP-EXTRACTION ENGINE)

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
    Advanced Legal & Financial Forensic Ontology Engine tailored for Kosovo Jurisdiction.
    Extracts high-resolution evidence webs, procedural actors, money flows, and legal contradictions.
    """

    def _clean_entity_name(self, name: str) -> str:
        """Pastron parashtesat procedurale për të shmangur duplikimet e personave."""
        if not name:
            return ""
        clean = name.strip()
        prefixes = [
            r"^(i|e)\s+pandehur(i|a)\s+",
            r"^(i|e)\s+dëmtuar(i|a)\s+",
            r"^paditës(i|ja)\s+",
            r"^i\s+paditur(i)?\s+",
            r"^dëshmitar(i|ja)\s+",
            r"^avokat(i)?\s+",
            r"^prokuror(i)?\s+",
            r"^gjyqtar(i|ja)\s+",
            r"^ekspert(i)?\s+",
            r"^dr\.\s+",
            r"^prof\.\s+"
        ]
        for p in prefixes:
            clean = re.sub(p, "", clean, flags=re.IGNORECASE)
        return clean.strip()

    def extract_ontology_from_text(self, text: str, doc_id: str = "", doc_name: str = "") -> Dict[str, Any]:
        if not text or not text.strip():
            return {"nodes": [], "edges": []}

        # Lexon deri në 60,000 karaktere (~20 faqe A4) për dokument
        safe_text = text[:60000]

        system_prompt = """
        Ti je Krye-Auditori dhe Eksperti Forenzik i Graph-it të Provave Ligjore për Gjykatat dhe Prokuroritë e Republikës së Kosovës (Juristi AI Evidence Matrix).
        DETYRA JOTE: Analizo me saktësi kirurgjike këtë dokument/aktakuzë/ekspertizë dhe nxirr TË GJITHË personat, institucionet, llogaritë, shkeljet dhe KONTRADIKTAT.

        KATEGORITË E ENTITETEVE (type):
        1. "PERSON": Çdo individ i përmendur (Paditësi, I Padituri, I Pandehuri, Dëshmitari, Avokati, Prokurori, Gjyqtari, Eksperti, Pronari).
        2. "ORGANIZATION": Institucionet shtetërore (Gjykata, Prokuroria, Ministritë, Policia, QKUK) dhe Kompanitë private / ARBK.
        3. "ACCOUNT": Llogaritë bankare, IBAN, faturat, transaksionet financiare, tenderët publikë.
        4. "LOCATION": Adresat, qytetet, pronat e paluajtshme, parcelat kadastrale.
        5. "EVENT": Seancat gjyqësore, marrëveshjet, aktakuzat, incidentet/veprat penale.
        6. "DOCUMENT": Kontratat, faturat, ekspertizat mjekoligjore/financiare, certifikatat e vdekjes/pronësisë.

        RELACIONET LIGJORE NË SHQIP (relation):
        - Procedurale: "PADITËS_I", "I_PADITUR_NGA", "PËRFAQËSOHET_NGA", "BASHKËPANDEHUR_ME", "DËSHMITAR_I", "GJYKUAR_NGA", "PUNËSUAR_NË"
        - Familjare/Shoqërore: "PRIND_I", "FËMIJË_I", "BASHKËSHORT_I", "LIDHJE_FAMILJARE", "BASHKËPUNTOR_I"
        - Pronësi & Financa: "PRONAR_I", "TRANSFER_PARASH", "FITUES_I_TENDERIT", "I_DETYROHET"
        - KONTRADIKTA & SHKELJE: "KUNDËRTHËNIE_ME_PROVËN", "MOSPËRPUTHJE_DËSHMIE", "SHKELJE_LIGJORE", "DENONCUAR_NGA"

        Përgjigju VETËM në formatin JSON të pastër:
        {
          "nodes": [
            {
              "id": "slug_unike",
              "label": "Emri zyrtar (p.sh. Shaban Bala, Gjykata Themelore Prishtinë)",
              "type": "PERSON | ORGANIZATION | ACCOUNT | LOCATION | EVENT | DOCUMENT",
              "description": "Roli i saktë ligjor i nxjerrë nga dokumenti"
            }
          ],
          "edges": [
            {
              "source": "id_e_nyjes_burim",
              "target": "id_e_nyjes_synim",
              "relation": "RELACIONI_NË_SHQIP",
              "amount_eur": 15000.0,
              "date_iso": "YYYY-MM-DD",
              "evidence_text": "Citati tekstual nga dokumenti që e vërteton këtë lidhje ose kontradiktë"
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
        """Bashkon entitetet nga shumë dokumente duke ruajtur të gjitha referencat dhe përshkrimet."""
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

    def get_case_graph(self, db: Database, case_id: str) -> Dict[str, Any]:
        """Merr të gjithë ontologjinë e unifikuar të lëndës."""
        try:
            # 1. Kontrollo së pari në depon qendrore `db.case_graphs`
            graph_record = db.case_graphs.find_one({"case_id": case_id})
            if graph_record and graph_record.get("nodes"):
                return {
                    "nodes": graph_record.get("nodes", []),
                    "edges": graph_record.get("edges", []),
                    "updated_at": graph_record.get("updated_at")
                }

            # 2. Fallback te `db.cases`
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

            # 1. Titulli
            elements.append(Paragraph("Raporti i Ontologjisë Ligjore", title_style))
            elements.append(Paragraph(f"Lënda: <b>{c_title}</b> &nbsp;|&nbsp; Data e Gjenerimit: <b>{now_str}</b>", meta_style))
            elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563eb'), spaceAfter=14))

            # 2. Tabela e Entiteteve
            elements.append(Paragraph(f"1. REGJISTRI I ENTITETEVE TË DOKUMENTUARA ({len(nodes)})", section_heading))

            entity_table_data = [
                [Paragraph("<b>#</b>", cell_bold), Paragraph("<b>EMRI ZYRTAR</b>", cell_bold), Paragraph("<b>LLOJI</b>", cell_bold), Paragraph("<b>PËRSHKRIMI / ROLI LIGJOR</b>", cell_bold)]
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

            # 3. Tabela e Marrëdhënieve dhe Kontradiktave
            total_eur = sum(e.get("amount_eur", 0.0) or 0.0 for e in edges)
            fin_summary_str = f" (Sasia totale e transaksioneve: €{total_eur:,.2f})" if total_eur > 0 else ""

            elements.append(Paragraph(f"2. HARTA E LIDHJEVE DHE KANALEVE FINANCIARE ({len(edges)}){fin_summary_str}", section_heading))

            rel_table_data = [
                [Paragraph("<b>#</b>", cell_bold), Paragraph("<b>BURIMI</b>", cell_bold), Paragraph("<b>LIDHJA / TRANSAKSIONI</b>", cell_bold), Paragraph("<b>CAKU</b>", cell_bold), Paragraph("<b>PROVA ORIGJINALE / CITATI</b>", cell_bold)]
            ]

            for i, e in enumerate(edges, 1):
                raw_src = str(e.get("source", ""))
                raw_tgt = str(e.get("target", ""))
                src_label = node_label_map.get(raw_src, raw_src)
                tgt_label = node_label_map.get(raw_tgt, raw_tgt)

                rel = e.get("relation") or "LIDHJE"
                amt = f"<br/><font color='#059669'><b>€{e['amount_eur']:,.2f}</b></font>" if e.get("amount_eur") else ""
                evidence = e.get("evidence_text") or "I dokumentuar në fashikullin e lëndës."

                is_contradiction = "CONTRADICT" in rel or "KUNDËR" in rel or "MOSPËRPUTHJE" in rel
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
                disclaimer_text = "Ky raport është për referencë ligjore dhe duhet të verifikohet nga avokati mbrojtës."
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