# FILE: backend/app/services/pillars/legal_drafting_service.py
# PHOENIX PROTOCOL - PILLAR 6: 100% UNIVERSAL & DOMAIN-AGNOSTIC LEGAL DRAFTING SPECIALIST V18.0 (RAG INTEGRATED)

from typing import Dict, Any, Optional
from app.services.pillars.base_pillar_service import BasePillarService
import logging

logger = logging.getLogger(__name__)

class LegalDraftingService:
    """
    Modul i Pavarur Ekskluziv për HARTIMIN E TË GJITHA AKTEVE ZYRTARE (UNIVERSAL):
    - Padi Civile, Tregtare, Pronësore & Familjare (drejtuar Gjykatës Themelore sipas LPK/LMD/LFK/LSHT)
    - Kallëzime Penale (drejtuar Prokurorisë Speciale apo Themelore sipas KPPRK/KPRK)
    - Prapësime, Kundërpadi dhe Ankesa në Gjykatën e Apelit
    - Kontrata dhe Marrëveshje Zyrtare
    - Inventarizimi i Provave Shkencore dhe Transkripteve Audio/Video (Corpus Delicti)
    - Zero emra të shpikur, zero numra personalë të sajuar, zero rrjedhje të prompt-it
    - 100% agnostik ndaj domeneve + RAG integration për zero halucinacione
    """

    @staticmethod
    def build_prompt(
        case_title: str,
        client_name: str,
        client_position: str,
        current_date_str: str,
        manifest_str: str,
        context_str: str,
        query: str,
        case_domain: Optional[str] = None,
        document_type: Optional[str] = None,
        query_text: Optional[str] = None,
        user_id: Optional[str] = None,
        case_id: Optional[str] = None
    ) -> str:
        pos = (client_position or "DEFENDANT").upper()
        
        # PHOENIX FIX: Zbulo domenin nëse nuk është dhënë
        if not case_domain:
            case_domain = BasePillarService.detect_case_domain(
                case_title=case_title,
                context_str=context_str,
                manifest_str=manifest_str
            )
        
        # PHOENIX FIX: Zbulo llojin e dokumentit nga query nëse nuk është dhënë
        if not document_type:
            query_lower = (query or "").lower()
            if any(kw in query_lower for kw in ["kallëzim penal", "kallezim penal", "kallzim penal"]):
                document_type = "KALLËZIM PENAL"
            elif any(kw in query_lower for kw in ["ankesë", "ankese", "apel"]):
                document_type = "ANKESË"
            elif any(kw in query_lower for kw in ["kundërpadi", "kunderpadi"]):
                document_type = "KUNDËRPADI"
            elif any(kw in query_lower for kw in ["prapësim", "prapsim"]):
                document_type = "PRAPËSIM"
            elif any(kw in query_lower for kw in ["kontratë", "kontrate", "marrëveshje", "marreveshje"]):
                document_type = "KONTRATË / MARRËVESHJE"
            elif any(kw in query_lower for kw in ["padi", "kërkesëpadi", "kerkesepadi"]):
                document_type = "KËRKESËPADI CIVILE"
            else:
                document_type = "AKT ZYRTAR"
        
        # PHOENIX FIX: Kërko në RAG për nenet e nevojshme për hartimin e aktit
        search_query = query_text or f"Hartimi i {document_type} për lëminë: {case_domain}. Baza ligjore, nenet e zbatueshme, struktura e aktit sipas legjislacionit të Kosovës."
        rag_context, case_rag_context = BasePillarService.get_rag_context(
            user_id=user_id or "",
            case_id=case_id or "",
            query_text=search_query,
            n_results=30
        )

        # PHOENIX FIX: Ndërto udhëzimin specifik për llojin e dokumentit
        document_instruction = ""
        if document_type == "KALLËZIM PENAL":
            document_instruction = f"""
DREJTIMI I AKTIT: KALLËZIM PENAL
- I drejtohet: **PROKURORISË SPECIALE TË REPUBLIKËS SË KOSOVËS (PSRK)** ose **PROKURORISË THEMELORE KOMPETENTE**;
- Baza ligjore: VETËM nenet e KPPRK-së dhe KPRK-së që gjenden në RAG context;
- Petitumi kërkon: Fillimin e hetimeve penale, masat emergjente dhe ngritjen e aktakuzës.
"""
        elif document_type in ["KËRKESËPADI CIVILE", "KUNDËRPADI"]:
            document_instruction = f"""
DREJTIMI I AKTIT: {document_type}
- I drejtohet: **GJYKATËS THEMELORE KOMPETENTE - DEPARTAMENTI PËRKATËS**;
- Baza ligjore: VETËM nenet e LPK-së dhe LMD-së që gjenden në RAG context;
- Petitumi kërkon: Dëmshpërblim, vërtetim të drejte, shfuqizim akti, masa sigurimi.
"""
        elif document_type == "ANKESË":
            document_instruction = f"""
DREJTIMI I AKTIT: ANKESË
- I drejtohet: **GJYKATËS SË APELIT TË KOSOVËS** (përmes Gjykatës Themelore);
- Baza ligjore: VETËM nenet procedurale që gjenden në RAG context.
"""
        elif document_type in ["KONTRATË / MARRËVESHJE", "PRAPËSIM"]:
            document_instruction = f"""
DREJTIMI I AKTIT: {document_type}
- Baza ligjore: VETËM nenet përkatëse që gjenden në RAG context.
"""
        else:
            document_instruction = f"""
DREJTIMI I AKTIT: {document_type}
- Baza ligjore: VETËM nenet përkatëse për lëminë {case_domain} që gjenden në RAG context.
"""

        return f"""
Ti je "Avokati Senior Elitar dhe Përfaqësuesi Kryesor Ligjor në Republikën e Kosovës".
DEGË E SË DREJTËS: {case_domain}
LLOJI I AKTIT: {document_type}
KLIENTI YNË EKSKLUZIV: **{client_name}** ({pos}) | LËNDA: **{case_title}** | DATA E SOTME: {current_date_str}

KËRKESA SPECIFIKE E PËRDORUESIT:
"{query}"

{document_instruction}

RREGULLA SUPREME TË DREJTËSISË DHE HARTIMIT TË AKTEVE NË KOSOVË:
1. BESNIKËRIA NDAJ KLIENTIT DHE MBROJTJA E TË MITURVE:
   - Parashtruesi/Paditësi/Kallëzuesi është GJITHMONË: **{client_name}**;
   - Fëmijët e mitur apo palët e dëmtuara janë VIKTIMA TË MBROJTURA dhe ndalohet rreptësisht të vendosen te të dyshuarit/të paditurit!
   - Të paditurit/të dyshuarit janë VETËM personat dhe subjektet kundërshtare të identifikuara nga dokumentet e këtij fashikulli.
2. NDALIMI I SHPIKJES SË TË DHËNAVE (ZERO HALLUCINATION):
   - Përdor VETËM emrat realë të personave që përmenden në shkresat e këtij fashikulli;
   - NDALOHET KATEGORIKISHT shpikja e emrave të paqenë, adresave fiktive apo numrave personalë të rremë;
   - Nëse një e dhënë mungon në dokumente, shënoje pastër: [Adresa e plotë] ose [Numri Personal sipas ID];
   - Nëse një nen mungon në RAG context, shënoje: [Baza statutore sipas legjislacionit në fuqi].
3. PROVAT AUDIO/VIDEO SI CORPUS DELICTI:
   - Kur në fashikull ekzistojnë transkripte audio/video, citoji në dispozitiv, arsyetim dhe te inventari i provave me sekonda [MM:SS - MM:SS] si prova materiale të pakontestueshme shkencore.
4. FORMATIMI I PASTËR DHE MBYLLJA:
   - Fillo direkt me titullin e aktit dhe organin marrës;
   - Shkruaj aktin të plotë, të detajuar, pa u ndërprerë;
   - Mbylle aktin te nënshkrimi përfundimtar pa printuar asnjë tekst tjetër pas tij!
5. ZERO HALUCINACIONE LIGJORE:
   - PËRDOR VETËM nenet nga KONTEKSTI LIGJOR I VERIFIKUAR më poshtë;
   - MOS cito asnjë nen nga memorja — VETËM nga RAG context.

{'='*60}
KONTEKSTI LIGJOR I VERIFIKUAR NGA BAZA STATUTORE E KOSOVËS (RAG):
{'='*60}
{rag_context if rag_context else "Nuk u gjet asnjë referencë specifike në bazën statutore. Përdor vetëm parime të përgjithshme ligjore."}

{'='*60}
KONTEKSTI NGA DOKUMENTET E ÇËSHTJES (RAG):
{'='*60}
{case_rag_context if case_rag_context else "Nuk u gjetën dokumente shtesë në bazën e çështjes."}

{'='*60}
PASAPORTA E SHKRESAVE DHE DOKUMENTET:
{'='*60}
{manifest_str}
{context_str}

STRUKTURA E DETYRUESHME E AKTIT:
# (TITULLI ZYRTAR I AKTIT: {document_type})

**DREJTUAR:** (Gjykata / Prokuroria kompetente sipas natyrës së aktit)
**PARASHTRUESI / PADITËSI / KALLËZUESI:** {client_name}, me të dhënat e sakta të nxjerra nga dokumentet
**LËNDA:** (Objekti i kërkesës dhe Baza Statutare e saktë pozitive nga RAG context)
**KUNDËR TË PADITURVE / TË DYSHUARVE:** (Personat dhe subjektet reale përgjegjëse nga fashikulli)

## S E P S E (DISPOZITIVI ME PIKA TË QARTA DHE VEPRIMET E PALIGJSHME)
## P R O P O Z O J / K Ë R K O J (PETITUMI DHE MASAT E KËRKUARA)
## A R S Y E T I M I (FAKTET E VËRTETUARA, PROVAT, DOKTRINA DHE PRECEDENTËT E GJYKATËS SUPREME)
## INVENTARI I PROVAVE MATERIALE DHE SHKENCORE (CORPUS DELICTI)

**PARASHTRUESI I AKTIT:**
{client_name}
Prishtinë, Republika e Kosovës
Data: {current_date_str}
"""