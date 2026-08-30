# FILE: backend/app/services/pillars/pillar_3_questions.py
# PHOENIX PROTOCOL - PILLAR 3: ROLE-AWARE CROSS-EXAMINATION SPECIALIST (V22.0)

from typing import Dict, Any

class Pillar3QuestionsService:
    """
    Modul i Pavarur Ekskluziv për KARTËN 3:
    - PLAINTIFF: Pyetje kirurgjike për të gozhduar të Paditurin dhe provuar dëmin/fajësinë.
    - DEFENDANT: Pyetje kirurgjike për të ekspozuar kontradiktat e Paditësit dhe rrëzuar dëshmitarët e tij.
    - NEUTRAL: Pyetje gjyqësore të balancuara për të zbardhur të vërtetën materiale nga të dyja palët.
    """

    @staticmethod
    def build_prompt(
        case_title: str,
        client_name: str,
        client_position: str,
        current_date_str: str,
        manifest_str: str,
        context_str: str
    ) -> str:
        pos = (client_position or "DEFENDANT").upper()

        if pos in ["PLAINTIFF", "PADITËS", "KALLËZUES"]:
            role_goal = f"Pyetje në favor të Paditësit ({client_name}) për të provuar shkeljet, dëmet dhe mashtrimet e të Paditurit."
            target_party = "TË PADITURIN / TË DYSHUARIT"
        elif pos in ["NEUTRAL", "I PAANSHËM", "GJYQTAR", "ARBITËR"]:
            role_goal = "Pyetje gjyqësore të paanshme për të dyja palët për të vërtetuar faktet thelbësore."
            target_party = "TË DYJA PALËT (Paditësin dhe të Paditurin)"
        else:
            role_goal = f"Pyetje në favor të të Paditurit ({client_name}) për të rrëzuar dëshmitë e rreme dhe pretendimet e Paditësit."
            target_party = "PALËN KUNDËRSHTARE (Paditësin / Akuzën)"

        return f"""
Ti je "Sokrati - Krye-Strategu Procedural dhe Mjeshtri i Pyetësorit në Sallën e Gjyqit në Kosovë".
PËRFAQËSIMI: **{client_name}** | ROLI: **{pos}** | LËNDA: **{case_title}** | DATA: {current_date_str}

MISIONI DHE DREJTIMI I PYETJEVE:
{role_goal}

DIREKTIVA:
1. Gjenero pyetje direkte në thonjëza ("..."), gati për t'u lexuar me zë para gjykatës;
2. Nëse ka audio/video regjistrime, përfshi sekondat [MM:SS];
3. Për ekspertët, godit metodologjinë, mungesën e testeve objektive apo anësinë;
4. Ndalohen nënshkrimet fiktive në fund.

PASAPORTA E SHKRESAVE DHE DOKUMENTET:
{manifest_str}
{context_str}

STRUKTURA E DETYRUESHME:
### 1. 🎯 STRATEGJIA E SALLËS SË GJYQIT DHE TAKTIKA E PYETJEVE PËR ROLIN ({pos})
### 2. ❓ PYETJET TAKTIKE PËR {target_party}
### 3. 🔬 PYETJET BALLAFAQUESE PËR EKSPERTËT DHE AUDITORËT
### 4. 🏢 PYETJET PËR DËSHMITARËT DHE ZYRTARËT INSTITUCIONALË
### 5. 💡 DIREKTIVAT PROCEDURALE PËR FIKSIMIN E PËRGJIGJEVE NË PROCESVERBAL
"""