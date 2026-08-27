# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - 100% UNIVERSAL ENGINE V116.0 (ACCURATE 4-PILLAR PROGRESSIVE REDUCTION: 3->2->1->0)

import os
import sys
import asyncio
import logging
import re
from typing import List, Optional, Dict, Any, AsyncGenerator, Tuple
from datetime import datetime, timezone
from bson import ObjectId
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

API_KEY = settings.OPENROUTER_API_KEY or os.environ.get("OPENROUTER_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "deepseek/deepseek-chat" 
LLM_TIMEOUT = 90

AI_DISCLAIMER = "\n\n---\n*Kjo analizë ligjore është gjeneruar nga Juristi AI bazuar në shkresat e fashikullit dhe Jurisprudencën e Gjykatës Supreme të Kosovës, është për referencë dhe duhet të verifikohet.*"

MAX_CONTEXT_CHARS = 140_000 


class AlbanianRAGService:
    def __init__(self, db: Any):
        self.db = db
        
        if API_KEY:
            self.client = AsyncOpenAI(
                api_key=API_KEY,
                base_url=OPENROUTER_BASE_URL,
                timeout=LLM_TIMEOUT
            )
            logger.info("✅ [RAG] Universal Legal Engine V116.0 initialized with Exact Progressive Pill Reduction.")
        else:
            self.client = None
            logger.error("❌ [RAG] AI Engine failed to initialize: Missing API Key.")

    def _detect_user_intent(self, query: str) -> str:
        q = query.lower()
        
        explicit_draft_triggers = [
            "ma harto", "ma gjenero", "shkruaj aktin", "përpilo aktin", 
            "përgatit shkresën zyrtare", "harto padinë", "harto kërkesëpadinë",
            "harto kallëzimin penal", "harto prapësimin", "harto ankesën", "harto kontratën"
        ]
        if any(k in q for k in explicit_draft_triggers):
            return "DRAFTING"
        
        audit_keywords = [
            "direktivë e forenzikës ligjore", "direktivë e detyrueshme forenzike", 
            "paralajmërime & sugjerime", "lapsuseve", "shkelje procedurale"
        ]
        if any(k in q for k in audit_keywords):
            return "FORENSIC_AUDIT"
        
        # EXACT 4-PILLAR INTENT DETECTION
        if any(k in q for k in [
            "pyetësorin taktik", "pyetësor", "pyetje taktike", "ballafaqim", 
            "dëshmitarët", "marrja në pyetje", "seancë", "kundër-pyetje", "pyetjet taktike të ballafaqimit"
        ]):
            return "PILLAR_QUESTIONS"
        
        if any(k in q for k in [
            "llogarit dëmet", "llogaritja e dëmit", "lmd", "kamatën ligjore", 
            "masat emergjente", "dëmit material", "dëmet materiale e jomateriale", "sigurimin e kërkesëpadisë"
        ]):
            return "PILLAR_DAMAGES"

        if any(k in q for k in [
            "nxirr bazën e plotë ligjore", "baza statutore", "baza ligjore", 
            "jurisprudenca", "lapsuse në shkresa", "precedentët", "nenet e ligjit", "kushtetutën dhe konventat"
        ]):
            return "PILLAR_STATUTES"

        return "PILLAR_STRATEGY"

    def _optimize_query(self, query: str) -> str:
        cleaned = query.strip()
        preambles = [
            r"^\s*më\s+trego\s+rreth\s+",
            r"^\s*më\s+trego\s+për\s+",
            r"^\s*a\s+mund\s+të\s+më\s+ndihmosh\s+me\s+",
            r"^\s*ju\s+lutem\s+më\s+gjej\s+",
            r"^\s*kërko\s+për\s+",
            r"^\s*gjej\s+nenin\s+",
            r"^\s*shiko\s+nëse\s+",
            r"^\s*të\s+lutem\s+analizo\s+",
        ]
        for preamble in preambles:
            cleaned = re.sub(preamble, "", cleaned, flags=re.IGNORECASE)
        
        abbreviations = {
            r"\bLMD\b": "Ligji për Marrëdhëniet e Detyrimeve",
            r"\bKPRK\b": "Kodi Penal i Republikës së Kosovës (Nr. 06/L-074)",
            r"\bKPPRK\b": "Kodi i Procedurës Penale të Kosovës",
            r"\bLPK\b": "Ligji për Procedurën Kontestimore",
            r"\bLFK\b": "Ligji për Familjen i Kosovës",
            r"\bLSHT\b": "Ligji për Shoqëritë Tregtare",
        }
        for abbr, expansion in abbreviations.items():
            cleaned = re.sub(abbr, f"{abbr} ({expansion})", cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()

    def _get_expanded_text(self, d: Dict[str, Any]) -> str:
        metadata = d.get('metadata') or {}
        return (
            d.get('parent_text') or 
            metadata.get('parent_text') or 
            d.get('text') or 
            metadata.get('text') or 
            d.get('content') or 
            metadata.get('content') or 
            ""
        ).strip()

    def _build_context(self, case_docs: List[Dict], global_docs: List[Dict], db_documents: List[Dict]) -> Tuple[str, str]:
        manifest_lines = ["\n<<< REGJISTRI I SKEDARËVE DHE PASAPORTA FORENZIKE E FASHIKULLIT >>>\n"]
        context_blocks = []
        
        if db_documents:
            doc_budget = int((MAX_CONTEXT_CHARS * 0.70) / max(len(db_documents), 1))
            doc_budget = max(doc_budget, 7_000)
            
            for idx, doc in enumerate(db_documents, 1):
                doc_id = str(doc.get("_id", ""))
                file_name = doc.get("file_name") or doc.get("title") or f"Dokument_{idx}.pdf"
                doc_clickable_link = f"[{file_name}](/documents/{doc_id})"
                
                raw_t = (
                    doc.get("extracted_text") or 
                    doc.get("text_content") or 
                    doc.get("text") or 
                    doc.get("content") or 
                    ""
                ).strip()
                
                summ = (doc.get("summary") or "").strip()
                if summ == "Sinteza...":
                    summ = ""

                dense_passport = summ or raw_t[:1500] or "Shkresë e administruar në fashikull."
                manifest_lines.append(f"{idx}. {doc_clickable_link}: {dense_passport[:400]}")
                
                if len(db_documents) <= 15 and raw_t:
                    context_blocks.append(f"\n--- TEKSTI I PLOTË I SHKRESËS: {doc_clickable_link} ---\n{raw_t[:doc_budget]}\n")
        else:
            context_blocks.append("Nuk ka dokumente të bashkangjitura në fashikull.\n\n")

        context_blocks.append("\n<<< PARAGRAFET FORENZIKE DHE PROVAT E GJETA NGA KËRKIMI SEMANTIK NË FASHIKULL >>>\n")
        for d in case_docs:
            src = d.get('source') or 'Dokument'
            page_info = f", Faqja: {d.get('page')}" if d.get('page') else ""
            context_blocks.append(f"[{src}{page_info}]:\n{self._get_expanded_text(d)}\n")

        context_blocks.append("\n<<< BAZA STATUTARE DHE JURISPRUDENCA PARIMORE E GJYKATËS SUPREME TË KOSOVËS >>>\n")
        for d in global_docs:
            source_tag = d.get('source') or 'Burim Juridik'
            context_blocks.append(f"BURIMI: {source_tag}\nPËRMBAJTJA: {self._get_expanded_text(d)}\n")

        full_context = "".join(context_blocks)
        
        if len(full_context) > MAX_CONTEXT_CHARS:
            full_context = full_context[:MAX_CONTEXT_CHARS] + "\n[TË DHËNA TË PRERA PËR SHKAK TË MADHËSISË SË FASHIKULLIT]"

        return "\n".join(manifest_lines), full_context

    def _get_role_adapted_pillars(self, position: str) -> List[Tuple[str, str]]:
        pos = position.upper()
        if pos == "PLAINTIFF":
            p1 = "Identifiko të gjitha shtyllat kryesore ku mbështetet kërkesëpadia/kallëzimi ynë dhe matricën e plotë të provave."
            p2 = "Analizo bazën ligjore të kërkesëpadisë, afatet procedurale dhe nenet përkatëse të ligjeve të Kosovës."
            p3 = "Gjenero pyetjet taktike për të ballafaquar palën kundërshtare dhe dëshmitarët e saj në seancë."
            p4 = "Llogarit dëmet e kërkuara sipas ligjit dhe përgatit përmbledhjen ekzekutive mbi ecurinë e procedurës."
        elif pos == "NEUTRAL":
            p1 = "Analizo objektivisht gjendjen e lëndës, vendimet gjyqësore të marra dhe ballafaqimin e provave të administruara."
            p2 = "Vlerëso ligjshmërinë e pretendimeve të të dyja palëve, arsyetimet gjyqësore dhe barrën e provës sipas ligjit."
            p3 = "Identifiko mospërputhjet thelbësore dhe gjenero pyetje neutrale sqaruese për vërtetimin e fakteve."
            p4 = "Përgatit memorandumin objektiv të auditimit ligjor mbi lëndën dhe konkluzionet e paanshme."
        else:
            p1 = "Analizo të gjitha prapësimet kryesore të mbrojtjes, mungesën e provave të paditësit dhe faktet shfajësuese në fashikull."
            p2 = "Analizo bazën ligjore të prapësimeve, parashkrimin e afateve dhe nenet përkatëse për rrëzimin e padisë."
            p3 = "Gjenero kundër-pyetjet taktike për të zbuluar kontradiktat e pretendimeve dhe dëshmitarëve në seancë."
            p4 = "Përgatit përmbledhjen ekzekutive mbi rreziqet ligjore, shanset e mbrojtjes dhe hapat e mëtejshëm."

        return [
            ("PILLAR_1", p1),
            ("PILLAR_2", p2),
            ("PILLAR_3", p3),
            ("PILLAR_4", p4)
        ]

    def _determine_remaining_pills(self, query: str, position: str, history: Optional[List[Dict[str, Any]]] = None) -> List[str]:
        pillars = self._get_role_adapted_pillars(position)

        all_past_user_messages = []
        if history:
            for msg in history:
                if msg.get("role") == "user":
                    all_past_user_messages.append(str(msg.get("content", "")).lower())
        all_past_user_messages.append(query.lower())
        combined_text = " ".join(all_past_user_messages)

        remaining = []

        # MATCH PILLAR 1
        p1_triggers = [
            "shtyllat strategjike", "strategjia dhe matrica", "shtyllat kryesore", 
            "qëndrueshmërinë e lëndës", "gjendjen e lëndës", "mbështetet kërkesëpadia", 
            "faktet shfajësuese", "matricën e provave", "matricën e plotë të provave", "prapësimet kryesore"
        ]
        if not any(k in combined_text for k in p1_triggers):
            remaining.append(pillars[0][1])

        # MATCH PILLAR 2
        p2_triggers = [
            "nxirr bazën e plotë ligjore", "baza statutore", "baza ligjore", 
            "bazën ligjore të kërkesëpadisë", "bazën ligjore të prapësimeve", 
            "lapsuse në shkresa", "ligjshmërinë e pretendimeve", "precedentët dhe qëndrimet", "precedentët"
        ]
        if not any(k in combined_text for k in p2_triggers):
            remaining.append(pillars[1][1])

        # MATCH PILLAR 3
        p3_triggers = [
            "pyetësorin taktik", "pyetësori taktik", "pyetjet taktike", 
            "pyetjet taktike të ballafaqimit", "kundër-pyetjet", "marrja në pyetje", 
            "dëgjimin e dëshmitarëve", "mospërputhjet thelbësore"
        ]
        if not any(k in combined_text for k in p3_triggers):
            remaining.append(pillars[2][1])

        # MATCH PILLAR 4
        p4_triggers = [
            "llogarit dëmet", "llogaritja e dëmit", "dëmet materiale e jomateriale", 
            "kamatën ligjore vonesore", "masat emergjente", "masat emergjente mbrojtëse", 
            "sigurimin e kërkesëpadisë", "memorandumin objektiv"
        ]
        if not any(k in combined_text for k in p4_triggers):
            remaining.append(pillars[3][1])

        return remaining

    async def chat(self, query: str, user_id: str, case_id: Optional[str] = None,
                   document_ids: Optional[List[str]] = None, jurisdiction: str = 'ks',
                   history: Optional[List[Dict[str, Any]]] = None,
                   domain: Optional[str] = 'automatic') -> AsyncGenerator[str, None]:
        
        if not self.client:
            yield "Sistemi AI nuk është aktiv. Kontrolloni çelësat në Render."
            yield AI_DISCLAIMER
            return

        from app.services import vector_store_service, llm_service

        current_date_str = datetime.now(timezone.utc).strftime("%d.%m.%Y")

        client_position = "DEFENDANT"
        client_name = "Klienti"
        case_title = "Lënda Ligjore"
        case_desc = ""
        db_documents = []

        if case_id and self.db is not None:
            try:
                c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
                case_doc = self.db.cases.find_one({"_id": c_oid})
                if case_doc:
                    if case_doc.get("client_position") or case_doc.get("client_role"):
                        client_position = str(case_doc.get("client_position") or case_doc.get("client_role")).upper()
                    client_name = case_doc.get("client_name") or case_doc.get("client", {}).get("name") or client_name
                    case_title = case_doc.get("title") or case_doc.get("case_name") or case_title
                    case_desc = case_doc.get("description") or ""

                doc_filter: Dict[str, Any] = {
                    "$or": [{"case_id": case_id}, {"case_id": c_oid}], 
                    "status": {"$ne": "DELETED"}
                }

                if document_ids and len(document_ids) > 0:
                    doc_oids = [ObjectId(did) for did in document_ids if ObjectId.is_valid(did)]
                    doc_strs = [str(did) for did in document_ids]
                    doc_filter["_id"] = {"$in": doc_oids + doc_strs}

                doc_cursor = self.db.documents.find(doc_filter)
                db_documents = list(doc_cursor)
            except Exception as ex:
                logger.warning(f"Could not read case documents: {ex}")

        user_intent = self._detect_user_intent(query)
        optimized_query = self._optimize_query(query)

        case_docs = vector_store_service.query_case_knowledge_base(
            user_id=user_id, query_text=optimized_query, case_context_id=case_id, n_results=30
        )

        global_docs = vector_store_service.query_global_knowledge_base(
            query_text=optimized_query, n_results=16
        )

        manifest_str, context_str = self._build_context(case_docs, global_docs, db_documents)
        remaining_pills = self._determine_remaining_pills(query=query, position=client_position, history=history)

        # =========================================================================
        # ⚖️ METODOLOGJIA DOKTRINARE E JURISDIKSIONIT TË KOSOVËS (UNIVERSALE DHE DINAMIKE)
        # =========================================================================
        universal_doctrine_guidelines = """
        ⚖️ RREGULLA TË PËRGJITHSHME DOKTRINARE TË DREJTËSISË NË REPUBLIKËN E KOSOVËS:
        1. AUTONOMIA E PLOTË NGA SHKRESAT: Mos supozo asnjë fakt apo emër të jashtëm. Çdo person, pretendim, datë dhe shkelje duhet të burojë 100% nga dokumentet e fashikullit.
        2. DALLIMI I SFERËS CIVILE NGA AJO PENALE:
           - Nëse lënda është Kontestimore/Civile (Pronë, Dëmshpërblim, Kontrata, Familjare): Apliko LPK-në, LMD-në, LFK-në dhe standardin e barrës së provës. Shpifja/fyerja trajtohet ekskluzivisht sipas Ligjit Civil Nr. 02/L-17.
           - Nëse lënda përmban Shkelje Penale: Apliko KPRK (Ligji Nr. 06/L-074) dhe KPPRK (Ligji Nr. 08/L-032). Deklarimet e rreme ndiqen me Nenin 390/384, dokumentet e rreme mjekësore me Nenin 387, vendimet e paligjshme gjyqësore me Nenin 425, ushtrimi i ndikimit me Nenin 424, keqpërdorimi me Nenin 414.
        3. DISAMBIGUIMI I ENTITETEVE: Nëse dy persona në fashikull ndajnë të njëjtin mbiemër, ndalohet kategorikisht shkrirja e tyre. Izolo secilin sipas emrit të plotë dhe veprimeve procedurale.
        4. JURISPRUDENCA E GJYKATËS SUPREME: Zbato precedentët parimorë të Kolegjeve të Gjykatës Supreme të Kosovës mbi vlerësimin objektiv të provave dhe ndalimin e zbatimit të ligjit in malam partem.
        """

        # =========================================================================
        # 🏛️ PROMPTIMI UNIVERSAL DHE AGNOSTIK SIPAS 4 SHTYLLAVE JURIDIKE
        # =========================================================================

        if user_intent == "PILLAR_QUESTIONS":
            # KARTA 3: PYETËSORI TAKTIK I SEANCËS
            system_prompt = f"""
            Ti je "Sokrati - Krye-Strategu Procedural dhe Avokati Kryesor në Gjykatë në Kosovë".
            METADATAT E LËNDËS: **{case_title}** | Klienti: **{client_name}** ({client_position}) | Data: {current_date_str}

            {universal_doctrine_guidelines}

            MISIONI YT (KARTA 3 - PYETËSORI TAKTIK):
            Duke u bazuar EKSKLUZIVISHT në kontradiktat, procesverbalet dhe shkresat e këtij fashikulli, gjenero baterinë e plotë të pyetjeve taktike të ballafaqimit (Cross-Examination) për seancën e ardhshme.

            PASAPORTA DHE DOKUMENTET E FASHIKULLIT:
            {manifest_str}
            {context_str}

            STRUKTURA E PËRGJIGJES (E PËRSHTATUR DINAMIKISHT ME DOKUMENTET E LËNDËS):
            ### 1. 🎯 STRATEGJIA E BALLAFAQIMIT DHE PUNKTO-TAKTIKAT NË SEANCË
            ### 2. ❓ PYETJET TAKTIKE PËR PALËN KUNDËRSHTARE (Mbi mospërputhjet mes pretendimeve dhe provave materiale)
            ### 3. 🔬 PYETJET BALLAFAQUESE PËR EKSPERTËT / PROFESIONISTËT (Nëse ka ekspertiza mjekësore, financiare, gjeodezike apo teknike në fashikull)
            ### 4. 🏢 PYETJET PËR DËSHMITARËT DHE PERSONAT E PËRFSHIRË NGA SHKRESAT
            ### 5. 💡 KËSHILLA PROCEDURALE MBI PYETJET DHE REAGIMIN NË PROCESVERBAL
            """

        elif user_intent == "PILLAR_DAMAGES":
            # KARTA 4: LLOGARITJA E DËMIT DHE MASAT
            system_prompt = f"""
            Ti je "Sokrati - Eksperti Financiar-Juridik dhe Gjyqtari Suprem i Dëmshpërblimeve në Kosovë".
            METADATAT E LËNDËS: **{case_title}** | Klienti: **{client_name}** ({client_position}) | Data: {current_date_str}

            {universal_doctrine_guidelines}

            MISIONI YT (KARTA 4 - DËMI DHE MASAT):
            Duke u bazuar në të dhënat financiare, dëmet, pasojat dhe kërkesat e administruara në fashikull, përpilo llogaritjen e dëmit sipas Ligjit për Marrëdhëniet e Detyrimeve (LMD) bashkë me kamatën ligjore vonesore prej 8%, si dhe argumento masat emergjente mbrojtëse / sigurimin e kërkesëpadisë sipas LPK/KPPRK.

            PASAPORTA DHE DOKUMENTET E FASHIKULLIT:
            {manifest_str}
            {context_str}

            STRUKTURA E PËRGJIGJES:
            ### 1. 💶 TABELA E LLOGARITJES SË DËMIT MATERIAL / REAL (Shpenzimet, dëmi i drejtpërdrejtë, fitimi i humbur)
            ### 2. 🧠 TABELA E DËMIT JOMATERIAL (Cenimi i integritetit, dinjitetit, dhimbja shpirtërore apo e drejta prindërore/personale)
            ### 3. 📈 LLOGARITJA E KAMATËS LIGJORE VONESORE (8% në vit sipas LMD-së nga momenti i lindjes së detyrimit)
            ### 4. 🛡️ BAZA DHE ARSYETIMI PËR MASËN E SIGURISË / URDHËRIN MBROJTËS
            ### 5. 📋 PËRMBLEDHJA EKZEKUTIVE PËR KLIENTIN DHE REKOMANDIMI STRATEGJIK
            """

        elif user_intent == "PILLAR_STATUTES":
            # KARTA 2: BAZA STATUTARE DHE AUDITIMI PROCEDURAL
            system_prompt = f"""
            Ti je "Sokrati - Krye-Auditori Statutor dhe Doktrinar i Gjykatës Supreme të Kosovës".
            METADATAT E LËNDËS: **{case_title}** | Klienti: **{client_name}** ({client_position}) | Data: {current_date_str}

            {universal_doctrine_guidelines}

            MISIONI YT (KARTA 2 - BAZA LIGJORE DHE JURISPRUDENCA):
            Nxirr matricën e plotë statutore të aplikueshme për natyrën e këtij fashikulli (Kushtetuta, Ligjet përkatëse të Kosovës, Konventat), audito shkeljet procedurale dhe lapsuset formale në shkresa (Contra Legem), dhe lidh çdo shkelje me Jurisprudencën e Gjykatës Supreme të Kosovës.

            PASAPORTA DHE DOKUMENTET E FASHIKULLIT:
            {manifest_str}
            {context_str}

            STRUKTURA E PËRGJIGJES:
            ### 1. 📜 MATRICA STATUTARE E APLIKUESHME PËR KËTË LËNDË (Nenet, Ligjet e sakta të Kosovës dhe Kushtetuta)
            ### 2. ⚠️ AUDITIMI I SHKELJEVE PROCEDURALE DHE LAPSUSEVE NË SHKRESAT E LËNDËS
            ### 3. 🏛️ PRECEDENTËT DHE VENDIMET PARIMORE TË GJYKATËS SUPREME TË KOSOVËS
            ### 4. ⚖️ KUALIFIKIMI I SAKTË JURIDIK I PRETENDIMEVE DHE VEPRIMEVE TË PALËVE
            ### 5. 💡 DIREKTIVAT STRATEGJIKE MBI RRËZIMIN E VENDIMEVE APO FITOREN PROCEDURALE
            """

        elif user_intent == "DRAFTING":
            system_prompt = f"""
            ROLI YT: Avokat Senior dhe Përfaqësues Procedural Elitar në Republikën e Kosovës.
            KLIENTI YNË: **{client_name}** | POZICIONI: **{client_position}**
            MISIONI: Përdoruesi kërkon të HARTOSH një akt zyrtar gjyqësor të plotë dhe shterues bazuar në dokumentet e fashikullit.

            {universal_doctrine_guidelines}

            DOKUMENTET NË KONTEKST:
            {context_str}

            STRUKTURA E SHKRESËS ZYRTARE:
            - Organi Marrës | Palët e Plota | Titulli i Aktit | Baza Statutare e Saktë | Dispozitivi (SEPSE) | Arsyetimi Faktiq & Doktrinar | Petitumi/Kërkesa | Inventari i Provave | Rezervimi i Dëmit | Data dhe Nënshkrimi.
            """

        elif user_intent == "FORENSIC_AUDIT":
            system_prompt = f"""
            ROLI YT: Auditor i Forenzikës Ligjore dhe Gjyqtar i Kolegjit të Gjykatës Supreme të Kosovës.
            KLIENTI: **{client_name}** | POZICIONI: **{client_position}**
            MISIONI: Kryej auditimin e plotë forenzik ligjor mbi dokumentin e ngarkuar në mënyrë të izoluar dhe objektive.

            {universal_doctrine_guidelines}

            DOKUMENTI I IZOLUAR PËR AUDITIM:
            {context_str}

            STRUKTURA E DETYRUESHME E RAPORTIT FORENZIK ME 5 SEKSIONE:
            ### 1. PIKAT KRYESORE DHE PROVAT E ADMINISTRUARA
            ### 2. BAZA STATUTARE DHE NENET E SAKTA TË LIGJEVE TË KOSOVËS
            ### 3. ⚠️ AUDITIMI I SHKELJEVE PROCEDURALE DHE KONTRASTET NË VENDIM
            ### 4. 🏛️ VENDIMET PARIMORE TË GJYKATËS SUPREME TË KOSOVËS
            ### 5. REKOMANDIMI STRATEGJIK DHE HAPAT E ARDHSHËM PROCEDURALË
            """

        else:
            # KARTA 1: STRATEGJIA DHE MATRICA E PROVAVE
            if client_position == "PLAINTIFF":
                role_instructions = f"PERSPEKTIVA JURIDIKE: **PADITËS / KALLËZUES (Përfaqësuesi i {client_name}).**"
            elif client_position == "NEUTRAL":
                role_instructions = "PERSPEKTIVA JURIDIKE: **NEUTRAL (Auditor / Kolegji Gjyqësor).**"
            else:
                role_instructions = f"PERSPEKTIVA JURIDIKE: **I PADITUR / I DENONCUAR (Mbrojtësi i {client_name}).**"

            system_prompt = f"""
            Ti je "Sokrati - Krye-Strategu dhe Gjyqtari Suprem i Drejtësisë në Kosovë".
            METADATAT E LËNDËS: **{case_title}** | Klienti: **{client_name}** ({client_position}) | Data: {current_date_str}
            {role_instructions}

            {universal_doctrine_guidelines}

            MISIONI YT (KARTA 1 - STRATEGJIA DHE MATRICA E PROVAVE):
            Analizo dhe ndërto të gjitha shtyllat kryesore strategjike të këtij fashikulli, duke përfshirë çdo provë materiale, shkencore, kontraktuale apo dëshmitare të administruar në dokumente, dhe jep vlerësimin doktrinar mbi qëndrueshmërinë e lëndës.

            PASAPORTA E SHKRESAVE DHE DOKUMENTET:
            {manifest_str}
            {context_str}

            STRUKTURA E PËRGJIGJES:
            ### 1. 🏛️ SHTYLLAT KRYESORE STRATEGJIKE DHE QËNDRUESHMËRIA PROCEDURALE E LËNDËS
            ### 2. 🔬 MATRICA E PLOTË E PROVAVE MATERIALE, SHKENCORE DHE SHKRESORE NGA FASHIKULLI
            ### 3. 👥 IDENTIFIKIMI I TË GJITHË AKTORËVE, ROLEVE DHE PËRGJEGJËSIVE PROCEDURALE
            ### 4. 🔨 VLERËSIMI DOKTRINAR I GJYQTARIT SUPREM MBI SHANSET DHE RREZIQET E PROCESIT
            ### 5. 🎯 REKOMANDIMI STRATEGJIK DHE HAPAT E MENJËHERSHËM PËR VEPRIM
            """

        try:
            response = await self.client.chat.completions.create(
                model=OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": optimized_query}
                ],
                temperature=0.1,
                stream=True,
                max_tokens=8192
            )
            
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            # PROGRESIVITETI I SAKTË: 3 -> 2 -> 1 -> 0
            if user_intent in ["PILLAR_STRATEGY", "PILLAR_STATUTES", "PILLAR_QUESTIONS", "PILLAR_DAMAGES"] and remaining_pills and len(remaining_pills) > 0:
                pills_block = "\n\nSugjerime për Hapat e Ardhshëm:\n" + "\n".join([f"{idx + 1}. {pill}" for idx, pill in enumerate(remaining_pills)])
                yield pills_block

            yield AI_DISCLAIMER
        except Exception as e:
            logger.error(f"RAG Stream Failure: {e}")
            yield f"\n[Gabim Gjatë Gjenerimit: Motori i Inteligjencës Artificiale tejkaloi kapacitetin. Ju lutem provoni përsëri.]"
            yield AI_DISCLAIMER