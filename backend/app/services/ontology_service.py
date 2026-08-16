# FILE: backend/app/services/ontology_service.py
# PHOENIX PROTOCOL - DYNAMIC FORENSIC ONTOLOGY ENGINE (100% AGNOSTIC & ZERO HARDCODING)

import logging
import re
import io
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from pymongo.database import Database
from bson import ObjectId

from .llm_service import _call_llm_async, clean_and_parse_json, FAST_MODEL

logger = logging.getLogger(__name__)

VALID_ENTITY_TYPES = {"PERSON", "ORGANIZATION", "ACCOUNT", "LOCATION", "EVENT", "DOCUMENT"}

class OntologyService:
    """
    Universally Dynamic Forensic Knowledge Graph Engine.
    Operates strictly on uploaded document facts without case-specific bias or hardcoded entities.
    """

    def _clean_entity_name(self, name: str) -> str:
        if not name:
            return ""
        clean = name.strip()
        # Heq vetëm titujt dhe rolet procedurale nga fillimi i emrit për të mundësuar bashkimin
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

    def pack_documents_into_dynamic_buckets(self, docs: List[Dict[str, Any]], max_chars_per_bucket: int = 50000) -> List[Dict[str, Any]]:
        """Ndante 32 dokumentet në pako të menaxhueshme për dritaren e kontekstit."""
        buckets = []
        current_bucket_docs = []
        current_bucket_text = []
        current_chars = 0

        for doc in docs:
            doc_id = str(doc.get("_id"))
            doc_name = doc.get("file_name", "Dokument")
            txt = doc.get("extracted_text") or doc.get("text_content") or doc.get("summary") or ""
            
            if not txt.strip():
                continue

            doc_block = f"\n=== DOKUMENTI (ID: {doc_id}, Emri: {doc_name}) ===\n{txt}\n"
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
        Ti je një Arkitekt i Ontologjisë Ligjore dhe Hetues Forenzik i Specializuar.
        DETYRA: Analizo shkresat e dhëna dhe nxirr një Rrjet Dijesh të Strukturuar (Knowledge Graph).

        RREGULLAT E SEVERA KUNDËR SHPIKJEVE (ZERO HALLUCINATIONS):
        1. Përdor VETËM emrat, institucionet, datat, paratë dhe faktet që ndodhen LITERATISHT në tekst.
        2. Çdo lidhje midis nyjeve duhet të shoqërohet me citatin e saktë ("evidence_text") nga dokumenti.
        3. Të gjitha përshkrimet dhe relacionet duhet të jenë në Gjuhën Shqipe Zyrtare.

        KATEGORITË E NYJEVE ("type"):
        - "PERSON": Individë (palë, dëshmitarë, zyrtarë, mjekë, ekspertë).
        - "ORGANIZATION": Kompani, gjykata, prokurori, institute, stacione policore, spitale.
        - "DOCUMENT": Shkresa konkrete, kontrata, raporte mjekësore, fatura, vendime, ekspertiza.
        - "LOCATION": Vende, qytete, adresa ku kanë ndodhur ngjarjet.
        - "EVENT": Ngjarje specifike, takime, seanca gjyqësore, incidente.
        - "ACCOUNT": Llogari bankare ose mjete financiare.

        FORMATI I KËRKUAR JSON:
        {
          "nodes": [
            {
              "id": "slug_unike",
              "label": "Emri zyrtar i entitetit",
              "type": "PERSON",
              "description": "Roli ose veprimi i saktë i këtij entiteti sipas shkresës"
            }
          ],
          "edges": [
            {
              "source": "slug_unike_e_burimit",
              "target": "slug_unike_e_synimit",
              "relation": "RELACIONI_NË_SHQIP",
              "amount_eur": null,
              "date_iso": "YYYY-MM-DD ose E papërcaktuar",
              "evidence_text": "Citat direkt nga teksti që provon këtë lidhje"
            }
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
                    "source_doc_ids": doc_ids,
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
                    "source_doc_ids": doc_ids
                })

            return {"nodes": valid_nodes, "edges": valid_edges}

        except Exception as e:
            logger.error(f"Error in extraction: {e}")
            return {"nodes": [], "edges": []}

    def merge_graph_data(self, existing_nodes: List[Dict], existing_edges: List[Dict], 
                         new_nodes: List[Dict], new_edges: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Bashkon entitetet nga të gjitha batch-et pa humbur të dhëna."""
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

    async def dynamically_synthesize_cross_document_contradictions(
        self, nodes: List[Dict], edges: List[Dict], case_title: str, all_docs: List[Dict] = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        MOTORRI UNIVERSAL I ZBULLIMIT TË KONTRADIKTAVE:
        Krahason faktet dhe dëshmitë midis dokumenteve të ndryshme bazuar VETËM në rregullat epistemologjike ligjore.
        """
        if not nodes or len(nodes) < 2:
            return nodes, edges

        node_ids = {n["id"] for n in nodes}
        edge_set = {f"{e['source']}___{e['target']}" for e in edges}
        updated_edges = list(edges)

        # Mbledh thelbin e dokumenteve për krahasim të plotë
        doc_digests = []
        if all_docs:
            for d in all_docs:
                fname = d.get("file_name", "Dokument")
                txt = (d.get("extracted_text") or d.get("text_content") or d.get("summary") or "")[:2000]
                if txt.strip():
                    doc_digests.append(f"SKEDARI: {fname}\nPËRMBAJTJA:\n{txt}\n")

        dossier_text = "\n".join(doc_digests)
        nodes_list_str = "\n".join([f"- {n['label']} (ID: {n['id']}, Lloji: {n['type']})" for n in nodes[:80]])

        prompt = f"""
        Ti je një Hetues Forenzik dhe Auditor i Provave Gjyqësore. Çështja: "{case_title}".

        PËRMBLEDHJA E DOKUMENTEVE TË FASHIKULLIT:
        {dossier_text}

        LISTA E NYJEVE TË IDENTIFIKUARA NË GRAF:
        {nodes_list_str}

        DETYRA JOTE FORENZIKE:
        Krahaso provat e dokumenteve me njëra-tjetrën dhe zbulo KONTRADIKTAT FAKTIKE, KOHORE dhe PROCEDURALE.

        RREGULLAT LOGJIKE PËR KRIJIMIN E LIDHJES SË KONTRADIKTËS:
        1. KONTRADIKTË KOHORE / ALIBI: Kur Personi A thotë se ishte në Vendin X në Datën/Orën T, por një dokument, raport apo dëshmitar tjetër vërteton se ishte në Vendin Y.
           -> [Burimi_Provë/Dëshmi] --("KUNDËRTHËNIE_KOHORE")--> [Personi/Pretendimi]
        2. KONTRADIKTË FAKTIKE ME PROVËN MATERIALE: Kur një palë pretendon një fakt (p.sh. nuk ka marrë para, nuk ka nënshkruar, nuk ka kryer veprim), por një provë shkencore/zyrtare (faturë, ekspertizë, raport mjekësor/policor) vërteton të kundërtën.
           -> [Dokumenti_Provë] --("KUNDËRTHËNIE_ME_PROVËN_MATERIALE")--> [Pretenduesi]
        3. NDRYSHIM DËSHMIE: Kur i njëjti person jep deklaratë në Dokumentin A që bie ndesh me atë që deklaron në Dokumentin B.
           -> [Dëshmia_B] --("NDRYSHIM_DËSHMIE")--> [Dëshmia_A]
        4. SHKELJE PROCEDURALE / DATASH: Kur një akt zyrtar ka mospërputhje datash administrative ose kundërshton vendimin paraprak.
           -> [Akti_I_Mëvonshëm] --("SHKELJE_PROCEDURALE_DATASH")--> [Akti_I_Mëparshëm]

        KTHE VETËM JSON NË SHQIP (Përdor ID-të e sakta nga lista e nyjeve më sipër):
        {{
          "contradiction_edges": [
            {{
              "source": "id_burimi_nga_lista",
              "target": "id_synimi_nga_lista",
              "relation": "KUNDËRTHËNIE_ME_PROVËN_MATERIALE | KUNDËRTHËNIE_KOHORE | NDRYSHIM_DËSHMIE | SHKELJE_PROCEDURALE_DATASH",
              "evidence_text": "Përshkrimi i saktë ligjor i mospërputhjes së provuar midis dokumenteve"
            }}
          ]
        }}
        """

        try:
            raw = await _call_llm_async(
                system_prompt="Ti je hetues ligjor i pavarur dhe objektiv i kontradiktave. Mos shpik asgjë.",
                user_content=prompt,
                json_mode=True,
                temperature=0.0,
                model=FAST_MODEL
            )
            parsed = clean_and_parse_json(raw)
            contradiction_edges = parsed.get("contradiction_edges", [])

            for ce in contradiction_edges:
                src = str(ce.get("source", "")).strip().lower()
                tgt = str(ce.get("target", "")).strip().lower()
                rel = str(ce.get("relation", "KUNDËRTHËNIE_ME_PROVËN")).upper().replace(" ", "_")
                ev = str(ce.get("evidence_text", ""))

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
                            "source_doc_ids": ["FORENSIC_CONTRADICTION_ENGINE"]
                        })
                        edge_set.add(key)
        except Exception as e:
            logger.error(f"Error in contradiction synthesis: {e}")

        # VËREJTJE: U hoq plotësisht algoritmi artificial BFS që krijonte lidhje false!
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
            logger.error(f"Error fetching graph for case {case_id}: {e}")
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

            doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=45)
            styles = getSampleStyleSheet()
            
            title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=14, leading=18, textColor=colors.HexColor('#0f172a'), spaceAfter=6)
            meta_style = ParagraphStyle('DocMeta', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=13, textColor=colors.HexColor('#475569'), spaceAfter=12)
            section_heading = ParagraphStyle('SectionHeading', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=11, leading=15, textColor=colors.HexColor('#0f172a'), spaceBefore=12, spaceAfter=8)
            cell_bold = ParagraphStyle('CellBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, leading=11, textColor=colors.HexColor('#0f172a'))
            cell_text = ParagraphStyle('CellText', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=11, textColor=colors.HexColor('#334155'))
            cell_italic = ParagraphStyle('CellItalic', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=8, leading=11, textColor=colors.HexColor('#475569'))
            cell_contradiction = ParagraphStyle('CellContradiction', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=11, textColor=colors.HexColor('#dc2626'))

            elements = []
            elements.append(Paragraph("Raporti i Ontologjisë Ligjore dhe Matrica e Provave", title_style))
            elements.append(Paragraph(f"Lënda: <b>{c_title}</b> &nbsp;|&nbsp; Data: <b>{now_str}</b>", meta_style))
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
                [Paragraph("<b>#</b>", cell_bold), Paragraph("<b>BURIMI</b>", cell_bold), Paragraph("<b>RELACIONI / MOSPERPUTHJA</b>", cell_bold), Paragraph("<b>CAKU</b>", cell_bold), Paragraph("<b>CITATI I PROVËS MATERIALE</b>", cell_bold)]
            ]

            for i, e in enumerate(edges, 1):
                raw_src = str(e.get("source", ""))
                raw_tgt = str(e.get("target", ""))
                src_label = node_label_map.get(raw_src, raw_src)
                tgt_label = node_label_map.get(raw_tgt, raw_tgt)

                rel = e.get("relation") or "LIDHJE"
                amt = f"<br/><font color='#059669'><b>€{e['amount_eur']:,.2f}</b></font>" if e.get("amount_eur") else ""
                evidence = e.get("evidence_text") or "I dokumentuar në fashikullin e lëndës."

                is_contradiction = (
                    "CONTRADICT" in rel or 
                    "KUNDËRTHËNIE" in rel or 
                    "MOSPËRPUTHJE" in rel or 
                    "FALSIFIKIM" in rel or 
                    "SHKELJE" in rel or 
                    "NDRYSHIM_DËSHMIE" in rel
                )
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