# FILE: backend/app/services/report_service/evidence_map_report.py
# PHOENIX PROTOCOL - EVIDENCE MAP REPORT GENERATOR (CLEAN TITLES & LEGAL DISCLAIMER)

import io
from datetime import datetime
from typing import Dict, Any, List

from .helpers import _get_text
from .strategy_report import create_pdf_from_text

def generate_evidence_map_report(case_id: str, map_data: Dict[str, Any], case_title: str = "N/A", lang: str = "sq") -> io.BytesIO:
    """Converts Evidence Map nodes/edges data into a structured Markdown report for PDF generation."""
    nodes = map_data.get('nodes', [])
    edges = map_data.get('edges', [])
    
    claims = [n for n in nodes if n.type == 'claimNode']
    evidence_nodes = {n['id']: n for n in nodes if n.type == 'evidenceNode'}
    
    report_parts: List[str] = []
    
    report_parts.append("# Raporti i Ontologjisë")
    report_parts.append(f"**Lënda:** {case_title}")
    report_parts.append(f"**Data e Gjenerimit:** {datetime.now().strftime('%d/%m/%Y')}")
    report_parts.append("\n---\n")

    report_parts.append(f"## {_get_text('map_section_claims', lang)}\n")
    
    if not claims:
        report_parts.append("*Asnjë pretendim nuk u gjet në hartë.*\n")
    
    for claim in claims:
        c_data = claim.get('data', {})
        claim_id = claim.get('id')
        proven_status = ' Vërtetuar' if c_data.get('isProven') else ' Pa Vërtetuar'
        
        report_parts.append(f"### {c_data.get('label', 'Pretendim pa Titull')} ({proven_status})")
        if c_data.get('content'):
            content_cleaned = c_data.get('content').replace('\n', ' ')
            report_parts.append(f"""> {content_cleaned}\n""")
        
        claim_edges = [e for e in edges if e.target == claim_id]
        relationships: Dict[str, List[Dict[str, Any]]] = {'supports': [], 'contradicts': [], 'related': []}

        for edge in claim_edges:
            source_id = edge.source
            if source_id in evidence_nodes:
                rel_type = edge.type or 'related'
                rel_label = edge.data.get('label', '') if edge.data else ''
                evidence = evidence_nodes[source_id]
                relationships[rel_type].append({'evidence': evidence, 'label': rel_label, 'strength': edge.data.get('strength', 3) if edge.data else 3})

        report_parts.append(f"#### {_get_text('map_section_evidence', lang)}\n")
        if all(not rels for rels in relationships.values()):
            report_parts.append("*Nuk ka prova të lidhura me këtë pretendim.*\n")
            
        for rel_type, rel_list in relationships.items():
            if not rel_list: continue
            header_key = f"map_rel_{rel_type}"
            header_text = _get_text(header_key, lang)
            report_parts.append(f"**{header_text} ({len(rel_list)})**\n")
            
            for item in rel_list:
                evd = item['evidence'].get('data', {})
                metadata = []
                if evd.get('exhibitNumber'): metadata.append(f"**{_get_text('map_exhibit', lang)}** {evd['exhibitNumber']}")
                if evd.get('isAuthenticated') is not None: 
                    status = 'Po' if evd['isAuthenticated'] else 'Jo'
                    metadata.append(f"**{_get_text('map_auth', lang)}** {status}")
                if evd.get('isAdmitted'): metadata.append(f"**{_get_text('map_admitted', lang)}** {evd['isAdmitted']}")
                
                content_line = f"* **{item['evidence'].get('data', {}).get('label', 'Provë pa Titull')}**"
                if metadata: content_line += f" ({' | '.join(metadata)})"
                report_parts.append(content_line)
                if item['label']: report_parts.append(f"  > *{_get_text('map_notes', lang)} {item['label']}*")
        
        report_parts.append("\n---\n")

    final_markdown = "\n".join(report_parts)
    return create_pdf_from_text(final_markdown, "Raporti i Ontologjisë")