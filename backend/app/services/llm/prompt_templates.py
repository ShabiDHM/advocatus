# FILE: backend/app/services/llm/prompt_templates.py
# PHOENIX PROTOCOL - PROMPT TEMPLATES V45.0 (PROACTIVE LITIGATION INTELLIGENCE • ZERO REFUSAL LOCK)

import re

AI_DISCLAIMER = "\n\n---\n*Kjo përgjigje është gjeneruar nga Juristi AI bazuar në shkresat e fashikullit dhe legjislacionin në fuqi të Republikës së Kosovës. Për përdorim profesional nga avokati.*"

def build_dynamic_identity_header(
    client_name: str = "Pala Kliente", 
    opposing_name: str = "Pala Kundërshtare", 
    position: str = "DEFENDANT"
) -> str:
    """
    PHOENIX ENGINE: Gjeneron identitetin strategjik të lëndës për avokatin mbrojtës / përfaqësuesin ligjor.
    Garanton përfaqësim me standardet më të larta të Gjykatës Supreme dhe Odës së Avokatëve të Kosovës.
    """
    pos_upper = (position or "DEFENDANT").upper()
    if pos_upper in ["DEFENDANT", "I_PADITUR", "MBROJTJE", "I_PANDEHUR"]:
        role_label = "I PADITUR / I PANDEHUR (MBROJTJE STRATEGJIKE)"
    elif pos_upper in ["PLAINTIFF", "PADITES", "PADITËS", "SULM", "I_DËMTUAR"]:
        role_label = "PADITËS / I DËMTUAR (PADIA DHE NDJEKJA)"
    else:
        role_label = f"PËRFAQËSUES LIGJOR ({pos_upper})"
    
    return f"""
[MANDATI DHE IDENTITETI I LËNDËS]
KLIENTI YNË ({role_label}): {client_name}.
PALA KUNDËRSHTARE: {opposing_name}.

[MANDATI RIGOROZ I AVOKATIT STRATEG]
1. Ti je këshilltari kryesor ligjor dhe përfaqësuesi strategjik i {client_name}.
2. Detyra jote është të analizosh me sy kritik çdo shkresë, procesverbal, ekspertizë dhe provë materiale në fashikull për të siguruar mbrojtjen absolute ligjore të {client_name}.
3. Çdo pretendim i palës kundërshtare ({opposing_name}) trajtohet si pretendim i kundërshtueshëm që duhet të çmontohet me bazë statutore dhe prova materiale/shkencore.
4. Përdor VETËM gjuhën standarde juridike shqipe të zbatueshme në Gjykatat dhe Prokuroritë e Republikës së Kosovës.
5. Mbështetu rigorozisht në ligjet pozitive të Kosovës (LPK Nr. 03/L-006, Kodi Penal Nr. 06/L-074, Kodi i Procedurës Penale Nr. 08/L-032, LMD Nr. 04/L-077, Ligji për Familjen Nr. 2004/32, LPP Nr. 04/L-139).
"""

UNBREAKABLE_IDENTITY_HEADER = build_dynamic_identity_header()

def _sanitize_and_disambiguate_prompt(user_text: str, opposing_name: str = "Pala Kundërshtare") -> str:
    """
    Pastron dhe qartëson referencat e tekstit për të eliminuar konfuzionin e palëve.
    """
    if not user_text:
        return ""
    
    cleaned = re.sub(r'\b(ai|aj)\s+vetë?\b', f'Pala Kundërshtare ({opposing_name})', user_text, flags=re.IGNORECASE)
    cleaned = re.sub(r'\b(kundërshtari|kundershtari)\b', f'Pala Kundërshtare ({opposing_name})', cleaned, flags=re.IGNORECASE)
    return cleaned