# FILE: backend/app/services/pillars/role_guard_service.py
# PHOENIX PROTOCOL - ROLE GUARD SERVICE V70.0 (3 DISTINCT PROCEDURAL STANCES • ZERO REFUSAL LOCK)

import logging
from typing import Optional, Dict, Any
from bson import ObjectId

logger = logging.getLogger(__name__)

VALID_ROLES = {
    "PLAINTIFF": "PADITËS",
    "PADITËS": "PADITËS",
    "PADITES": "PADITËS",
    "KALLËZUES": "PADITËS",
    "I DËMTUAR": "PADITËS",
    "DEFENDANT": "I PADITUR",
    "I PADITUR": "I PADITUR",
    "I PADITURI": "I PADITUR",
    "I PANDEHUR": "I PADITUR",
    "I DYSHUAR": "I PADITUR",
    "NEUTRAL": "NEUTRAL",
    "I PAANSHËM": "NEUTRAL",
    "GJYQTAR": "NEUTRAL",
    "ARBITËR": "NEUTRAL",
    "EKSPERT": "NEUTRAL"
}


class RoleGuardService:
    """
    Shërbimi i Përfaqësimit të 3 Roleve Procedurale (V70.0):
    1. PADITËS (Strategji Sulmi & Ndjekje Penale/Civile);
    2. I PADITUR (Mbrojtje e Hekurt & Rrëzim i Pretendimeve);
    3. NEUTRAL (Auditimi i Paanshëm i Gjyqtarit / Arbitrit).
    """

    @staticmethod
    def normalize_role(role: Optional[str]) -> str:
        if not role:
            return "I PADITUR"
        
        role_upper = role.upper().strip()
        return VALID_ROLES.get(role_upper, "I PADITUR")

    @staticmethod
    def get_role_from_case(case_id: str, db: Any) -> str:
        try:
            case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
            case = db.cases.find_one({"_id": case_oid})
            
            if not case:
                return "I PADITUR"
            
            raw_role = case.get("client_position") or case.get("role") or "DEFENDANT"
            return RoleGuardService.normalize_role(raw_role)
            
        except Exception as e:
            logger.error(f"❌ [RoleGuard] Gabim gjatë leximit të rolit: {e}")
            return "I PADITUR"

    @staticmethod
    def get_role_instruction(role: str, client_name: str) -> str:
        normalized = RoleGuardService.normalize_role(role)
        
        # 1. ROLI: PADITËS / SULM
        if normalized == "PADITËS":
            return f"""
QËNDRIMI STRATEGJIK: TI JE AVOKATI KRYESOR I PADITËSIT / PARASHTRUESIT ({client_name}).
MISIONI YT PROCEDURAL:
1. Ndërto strategjinë sulmuese për të PROVUAR plotësisht padinë/kallëzimin me prova të pakontestueshme materiale.
2. Identifiko dhe zbërthe të gjitha shkeljet ligjore, dëmet dhe përgjegjësinë e palës së denoncuar/të paditur.
3. Kërko masat emergjente mbrojtëse (Nenet 188 & 221 KPPRK / Masat e Sigurimit LPK) dhe maksimizo kompensimin e dëmit.
4. Çdo analizë dhe auditim synon të vulosë fitoren ligjore të {client_name}.
"""
        # 2. ROLI: I PADITUR / MBROJTJE
        elif normalized == "I PADITUR":
            return f"""
QËNDRIMI STRATEGJIK: TI JE AVOKATI KRYESOR MBROJTËS I TË PADITURIT / TË DYSHUARIT ({client_name}).
MISIONI YT PROCEDURAL:
1. Ndërto MBROJTJEN E HEKURT të {client_name} dhe rrëzo të gjitha pretendimet e palës kundërshtare.
2. Zbulo shkeljet thelbësore procedurale (Neni 384 KPPRK / Neni 182 LPK), provat e papranueshme dhe prapadatimet në shkresa.
3. Ndërto kundërsulmin procedural: Prapësime, Kundërpadi, Parashkrim dhe Kallëzime Penale për Lajmërim të Rremë.
4. Çdo analizë synon pafajësinë, hedhjen e aktit dhe refuzimin e kërkesave kundër {client_name}.
"""
        # 3. ROLI: NEUTRAL / GJYQTAR / EKSPERT
        else:
            return f"""
QËNDRIMI STRATEGJIK: TI JE GJYQTARI SUPREM / ARBITRI 100% I PAANSHËM DHE OBJEKTIV.
MISIONI YT PROCEDURAL:
1. Analizo dhe audito shkresat pa mbajtur anën e asnjërës palë, me sy të ftohtë doktrinar.
2. Peshon argumentet, ligjshmërinë e administrimit të provave dhe barrën e provës (Nenet 7, 8 & 319 LPK).
3. Identifiko pikat e forta, dobësitë dhe shkeljet ligjore të të dyja palëve në mënyrë të balancuar.
4. Jep vlerësimin e saktë doktrinar mbi qëndrueshmërinë e çështjes sipas ligjeve pozitive të Kosovës.
"""

    @staticmethod
    def build_role_guard(role: str, client_name: str) -> str:
        normalized = RoleGuardService.normalize_role(role)
        role_instruction = RoleGuardService.get_role_instruction(normalized, client_name)
        
        return f"""
{'='*60}
🛡️ POZICIONI PROCEDURAL I ZGJEDHUR: **{normalized}**
Klienti: **{client_name}**
{'='*60}
{role_instruction}

RREGULLAT E HEKURTA:
1. Përshtat analizën dhe tonin saktësisht sipas rolit të caktuar ({normalized}).
2. NDALOHET KATEGORIKISHT refuzimi i analizës. Çdo shkresë e ngarkuar duhet të auditohet në thellësi maksimale.
{'='*60}
"""

    @staticmethod
    def build_role_trace(role: str, client_name: str, case_domain: str = "") -> str:
        normalized = RoleGuardService.normalize_role(role)
        domain_part = f" | LËMIA: {case_domain}" if case_domain else ""
        return f"📌 ROLI: {normalized} | KLIENTI: {client_name}{domain_part}"

    @staticmethod
    def get_role_specific_tone(role: str) -> str:
        normalized = RoleGuardService.normalize_role(role)
        if normalized == "PADITËS":
            return "Toni: I vendosur, sulmues proceduralisht, i fokusuar në vërtetimin e padisë/kallëzimit."
        elif normalized == "I PADITUR":
            return "Toni: Mbrojtës, kirurgjikal, strategjik, i fokusuar në rrëzimin e pretendimeve të kundërshtarit."
        else:
            return "Toni: Objektiv, doktrinar, i paanshëm, i fokusuar në peshimin e barabartë të ligjit dhe provave."


role_guard_service = RoleGuardService()