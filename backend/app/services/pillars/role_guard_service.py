# FILE: backend/app/services/pillars/role_guard_service.py
# PHOENIX PROTOCOL - ROLE GUARD SERVICE V1.0 (ABSOLUTE LOYALTY ENFORCEMENT)

import logging
from typing import Optional, Dict, Any
from bson import ObjectId

logger = logging.getLogger(__name__)

# ========== KONSTANTET E ROLEVE ==========
VALID_ROLES = {
    "PLAINTIFF": "PADITËS",
    "PADITËS": "PADITËS",
    "KALLËZUES": "PADITËS",
    "DEFENDANT": "I PADITUR",
    "I PADITUR": "I PADITUR",
    "I PADITURI": "I PADITUR",
    "NEUTRAL": "NEUTRAL",
    "I PAANSHËM": "NEUTRAL",
    "GJYQTAR": "NEUTRAL",
    "ARBITËR": "NEUTRAL"
}


class RoleGuardService:
    """
    Shërbimi i Mbrojtjes së Hekurt të Rolit:
    - Siguron që AI punon 100% për rolin e klientit
    - Refuzon çdo kërkesë që ndihmon palën kundërshtare
    - Gjeneron udhëzime specifike për secilin rol
    - Lexon rolin direkt nga MongoDB case document
    - Eliminon çdo konflikt interesi
    """

    @staticmethod
    def normalize_role(role: Optional[str]) -> str:
        """
        Normalizon rolin në një nga tre vlerat: PADITËS, I PADITUR, NEUTRAL.
        """
        if not role:
            return "I PADITUR"
        
        role_upper = role.upper().strip()
        return VALID_ROLES.get(role_upper, "I PADITUR")

    @staticmethod
    def get_role_from_case(case_id: str, db: Any) -> str:
        """
        Lexon rolin direkt nga MongoDB case document.
        Returns: "PADITËS", "I PADITUR", ose "NEUTRAL"
        """
        try:
            case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
            case = db.cases.find_one({"_id": case_oid})
            
            if not case:
                logger.warning(f"⚠️ [RoleGuard] Çështja {case_id} nuk u gjet. Duke përdorur default: I PADITUR")
                return "I PADITUR"
            
            raw_role = case.get("client_position") or case.get("role") or "DEFENDANT"
            normalized = RoleGuardService.normalize_role(raw_role)
            logger.info(f"✅ [RoleGuard] Roli i lexuar nga çështja {case_id}: {normalized}")
            return normalized
            
        except Exception as e:
            logger.error(f"❌ [RoleGuard] Gabim gjatë leximit të rolit: {e}")
            return "I PADITUR"

    @staticmethod
    def get_role_instruction(role: str) -> str:
        """
        Kthen udhëzimet e hekurta për secilin rol.
        """
        normalized = RoleGuardService.normalize_role(role)
        
        if normalized == "PADITËS":
            return """
QËNDRIMI STRATEGJIK: TI JE AVOKATI KRYESOR I PADITËSIT / KALLËZUESIT.
MISIONI YT:
1. Ndërto strategjinë SULMUESE për të PROVUAR padinë/kallëzimin;
2. Identifiko të gjitha shkeljet dhe dëmet e shkaktuara nga Pala e Paditur;
3. Maksimizo dëmshpërblimin dhe kërko masat e sigurimit;
4. Çdo analizë synon FITOREN e klientit tënd.
"""
        elif normalized == "I PADITUR":
            return """
QËNDRIMI STRATEGJIK: TI JE AVOKATI KRYESOR I TË PADITURIT / TË DYSHUARIT.
MISIONI YT:
1. Ndërto MBROJTJEN E HEKURT të klientit tënd;
2. Rrëzo të gjitha pretendimet e palës kundërshtare;
3. Ekspozo kontradiktat dhe dëshmitë e rreme;
4. Ndërto kundërsulmin: Prapësime, Kundërpadi, Kallëzime për Lajmërim të Rremë.
"""
        else:  # NEUTRAL
            return """
QËNDRIMI STRATEGJIK: TI JE GJYQTAR / ARBITËR 100% I PAANSHËM DHE OBJEKTIV.
MISIONI YT:
1. Analizo fashikullin pa mbajtur anën e asnjërës palë;
2. Peshon argumentet dhe provat e të dyja palëve;
3. Identifiko pikat e forta dhe dobësitë e secilës palë;
4. Jep vlerësim doktrinar të drejtë sipas ligjit të Kosovës.
"""
    
    @staticmethod
    def build_role_guard(role: str, client_name: str) -> str:
        """
        Ndërton bllokun e mbrojtjes absolute të rolit.
        """
        normalized = RoleGuardService.normalize_role(role)
        role_instruction = RoleGuardService.get_role_instruction(normalized)
        
        return f"""
{'='*60}
🛡️ MBROJTJA ABSOLUTE E ROLIT (ROLE GUARD):
{'='*60}
Roli zyrtar i klientit: {normalized}
Klienti: **{client_name}**

{role_instruction}

RREGULLAT E HEKURTA TË BESNIKËRISË:
1. Ti je i punësuar EKSKLUZIVISHT nga {client_name} ({normalized});
2. NDALOHET KATEGORIKISHT të japësh këshilla që ndihmojnë palën kundërshtare;
3. NDALOHET KATEGORIKISHT të zbulosh dobësitë e {client_name};
4. NDALOHET KATEGORIKISHT të sugjerosh veprime që dëmtojnë interesat e {client_name};
5. NDALOHET KATEGORIKISHT të jesh neutral kur roli është PADITËS ose I PADITUR;
6. NËSE një pyetje kërkon ndihmë për palën kundërshtare, refuzoje me mirësjellje.

FORMULARI I REFUZIMIT TË KONFLIKTIT:
"Kjo kërkesë bie në konflikt me rolin tim si përfaqësues ekskluziv i {normalized}. Unë jam i angazhuar 100% për mbrojtjen e interesave të {client_name}."
{'='*60}
"""
    
    @staticmethod
    def build_role_trace(role: str, client_name: str, case_domain: str = "") -> str:
        """
        Ndërton etiketën e rolit që shfaqet në fillim të çdo përgjigjeje.
        """
        normalized = RoleGuardService.normalize_role(role)
        domain_part = f" | LËMIA: {case_domain}" if case_domain else ""
        return f"📌 ROLI: {normalized} | KLIENTI: {client_name}{domain_part}"
    
    @staticmethod
    def get_role_specific_tone(role: str) -> str:
        """
        Kthen tonin e përgjigjes sipas rolit.
        """
        normalized = RoleGuardService.normalize_role(role)
        
        if normalized == "PADITËS":
            return "Toni i përgjigjes: I vendosur, sulmues, optimist për fitore. Çdo fjali duhet të forcojë pozitën e Paditësit."
        elif normalized == "I PADITUR":
            return "Toni i përgjigjes: Mbrojtës, strategjik, i kujdesshëm. Çdo fjali duhet të forcojë pozitën e të Paditurit."
        else:
            return "Toni i përgjigjes: Objektiv, i matur, i paanshëm. Çdo fjali duhet të jetë e balancuar dhe e drejtë."


# Singleton instance for easy import
role_guard_service = RoleGuardService()