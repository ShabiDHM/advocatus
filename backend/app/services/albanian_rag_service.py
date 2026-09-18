# FILE: backend/app/services/albanian_rag_service.py
# PROTOKOLLI PHOENIX - SHËRBIMI DOKTRINAR RAG V276.0
# V276.0: Prompt i zgjeruar anti-halucinacion:
#         - Ndalohet zëvendësimi i ligjit me numër (03/L-182 ≠ 08/L-185).
#         - Kërkohet raportim i kontradiktave të brendshme (6 vs 12 muaj).
# V275.0: Prompt i fortë anti-halucinacion + rregulla strikte për citimet ligjore.
# V274.0: Chat-i kalon në FAST_SEARCH_MODEL (gpt-4o-mini).

import os
import logging
import re
from typing import List, Optional, Dict, Any, AsyncGenerator, Tuple
from datetime import datetime, timezone
from bson import ObjectId

from app.core.config import settings

from app.services.rag.intent_detector import IntentDetector
from app.services.rag.context_builder import ContextBuilder
from app.services.rag.response_generator import ResponseGenerator
from app.services.pillars.base_pillar_service import BasePillarService

from app.services.pillars.legal_drafting_service import LegalDraftingService
from app.services.pillars.statutory_verification_service import StatutoryVerificationService

from app.services.llm.llm_client import FAST_SEARCH_MODEL

logger = logging.getLogger(__name__)

CASE_CHAT_HISTORY_COLLECTION = "case_chat_history"

# ═══════════════════════════════════════════════════════════════════════════
# UDHËZIMI I BASHKËPUNIMIT + ANTI-HALUDINACIONI I FORTË (V276.0)
# ═══════════════════════════════════════════════════════════════════════════
NATURAL_COUNSEL_INSTRUCTION = """
UDHËZIME TË BASHKËPUNIMIT ME AVOKATIN DHE KLIENTIN:
1. BASHKËPUNIM I ZGJUAR DHE DIALOG I NATYRSHËM:
   - Dëgjoni me vëmendje kërkesën e përdoruesit. Nëse përdoruesi bën një pyetje paraprake, kërkon sqarim apo thotë se do të paraqesë një shkresë: përgjigjuni si një këshilltar i vërtetë njerëzor ligjor (pa shabllone mekanike dhe me mirëkuptim të plotë).
   - MOS sajo asnjëherë raporte imagjinare kur përdoruesi ende nuk e ka dhënë tekstin apo pyetjen konkrete.
2. SAKTËSI DHE BAZË LIGJORE:
   - Përgjigjuni në gjuhë standarde juridike të Republikës së Kosovës.
   - Mbështetuni në faktet reale të shkresave të lëndës dhe në dispozitat përkatëse.

═══════════════════════════════════════════════════════════════════════════
⚠️ RREGULLA TË PAFEKSIONUESHME ANTI-HALUDINACION (TË DETYRUESHME)
═══════════════════════════════════════════════════════════════════════════

1. PËRDOR VETËM NENET QË JANË NË KONTEKST:
   - Nëse në kontekstin e mësipërm nuk shfaqet neni konkret → NUK MUND TË CITOSH atë nen.
   - NUK LEJOHET të shpikësh numra neni, emra ligjesh, afate ose procedura që nuk shfaqen në kontekst.
   - Nëse informacioni mungon → thuaj:
     "Ky informacion nuk gjendet në shkresat e fashikullit. Rekomandohet verifikim me burimin zyrtar."

2. IDENTIFIKO SAKTËSISHT LIGJIN — KURRË MOS I NDËRRO:
   - **KPK**  = Kodi i Procedurës Penale (Nr. 08/L-032) → PROCEDURA PENALE
   - **KPRK** = Kodi Penal (Nr. 06/L-074)             → DËNIME, REHABILITIM, VEPRA PENALE
   - **LPK**  = Ligji për Procedurën Kontestimore (Nr. 03/L-006) → PROCEDURA CIVILE
   - **LMD**  = Ligji për Marrëdhëniet e Detyrimeve (Nr. 04/L-077) → DETYRIME, DËME, KONTRATA
   - **LMDHF** = Ligji për Mbrojtjen nga Dhuna në Familje (Nr. 03/L-182 → 08/L-185) → URDHRA MBROJTJEJE
   - **LFK**  = Ligji për Familjen (Nr. 2004/32)      → ÇËSHTJE FAMILJARE
   - **Kushtetuta** e Republikës së Kosovës           → TË DREJTAT THEMELORE

3. KURRË MOS PËRZIJ LËMIE LIGJORE:
   - NËSE çështja është CIVILE (prefiksi "C.nr." në numrin e lëndës, ose flet për urdhër mbrojtjeje, divorc, kujdestari) → NUK cito KPRK për dënime/rehabilitim.
   - NËSE çështja është PENALE (prefiksi "P.nr." ose "PKR") → NUK cito LPK për procedurë civile.
   - Rehabilitimi penal (fshirja e dënimit) NUK aplikohet në çështje civile.

4. ⚠️ LIGJET ME NUMËR (KRITIKE — V276.0):
   - KUR dokumenti citon "Ligji Nr. XX/L-YYY" → PËRDOR ATË NUMËR TË SAKTË.
   - NUK LEJOHET ta zëvendësosh me një version tjetër (të vjetër ose të re).
   - SHEMBULL: Nëse dokumenti shkruan "Ligji Nr. 03/L-182" → shkruaj "Ligji Nr. 03/L-182" — EDHE nëse e di që ekziston versioni i ri 08/L-185.
   - Roli yt është të raportosh ÇFARË THOTË DOKUMENTI, jo të përditësosh ligjin.
   - NUK LEJOHET të "normalizosh" ligjin duke e zëvendësuar me atë që ti e di si "më aktual".

5. FORMATO CITIMET SAKTËSISHT:
   - "Neni X i [Ligjit]" — KURRË "Neni X.Y".
   - Shembull i saktë: "Neni 15 i Ligjit Nr. 03/L-182", "Neni 29 i LMDHF-së".
   - Shembull i GABUAR: "Neni 93 i KPK-së" (kur në të vërtetë është KPRK).
   - Shembull i GABUAR: "Neni 29 i Ligjit Nr. 08/L-185" (kur dokumenti citon 03/L-182).

6. AFATET PROCEDURALE:
   - Cito afatin VETËM me burim: "Sipas [dokumenti/neni], afati është X".
   - NËSE dokumentet kanë afate të ndryshme → listoji TË GJITHA me burime.
   - NËSE nuk gjendet afat → shkruaj "Afati: kontrollo manualisht".

7. ⚠️ KONTRADIKTAT E BRENDSHME (KRITIKE — V276.0):
   - NËSE dokumenti ka kontradikta të brendshme (p.sh. "6 muaj" në një pikë, "12 muaj" në një tjetër) → LISTOJI TË DYJA dhe shëno me "⚠️ KONTRADIKTË NË DOKUMENT — PËR VERIFIKIM".
   - NUK LEJOHET të zgjedhësh njërën pa përmendur tjetrën.
   - Kjo ndihmon avokatin të identifikojë mangësitë e aktvendimit.

8. STRUKTURA E PËRGJIGJES:
   - Fillimisht identifiko çfarë pyet përdoruesi.
   - Pastaj jep përgjigjen e bazuar vetëm në kontekst.
   - Në fund, nëse ka dyshime → shkruaj "Për verifikim final konsultoni burimin zyrtar."

9. STATUSI I DOKUMENTIT:
   - NËSE dokumenti përmban "KËSHILLË JURIDIKE" ose "afat ankimi" → NUK është i plotfuqishëm.
   - MOS e etiketo si "i plotfuqishëm" pa bazë në tekst.

10. ZERO SHABLLONE TË PËRGJITHSHME:
    - NUK LEJOHET të shkruash përkufizime të përgjithshme ligjore që nuk lidhen me lëndën konkrete.
    - ÇDO fjali duhet të ketë lidhje me shkresat ose pyetjen e avokatit.
"""


def is_valid_legal_report(text: str) -> bool:
    if not text or len(text.strip()) < 150:
        return False

    lower_text = text.lower()
    error_markers = [
        "përkohësisht i ngarkuar",
        "error code:",
        "context_length_exceeded",
        "max_num_tokens",
        "upstream error",
        "not a valid model",
        "no endpoints found",
        "gabim teknik"
    ]
    for marker in error_markers:
        if marker in lower_text:
            return False

    return True


def detect_requested_pillar(query_lower: str) -> Optional[str]:
    if "shtjella 1" in query_lower or "shtjella_1" in query_lower or "ekzaminimi" in query_lower or "fakti" in query_lower:
        return "PILLAR_1"
    if "shtjella 2" in query_lower or "shtjella_2" in query_lower or "nenet" in query_lower or "shkeljet" in query_lower:
        return "PILLAR_2"
    if "shtjella 3" in query_lower or "shtjella_3" in query_lower or "kundërshtimet" in query_lower or "plani" in query_lower:
        return "PILLAR_3"
    return None


class AlbanianRAGService:
    def __init__(self, db: Any):
        self.db = db
        self.response_generator = ResponseGenerator()
        logger.info(f"✅ [RAG] Juristi AI Natural Client Service V276.0 Initialized (chat model: {FAST_SEARCH_MODEL}).")

    def _optimize_query(self, query: str) -> str:
        cleaned = query.strip()
        preambles = [
            r"^\s*më\s+trego\s+rreth\s+",
            r"^\s*më\s+trego\s+për\s+",
            r"^\s*a\s+mund\s+të\s+më\s+ndihmosh\s+me\s+",
            r"^\s*ju\s+lutem\s+më\s+gjej\s+",
            r"^\s*kërko\s+për\s+",
            r"^\s*gjej\s+nenin\s+",
        ]
        for preamble in preambles:
            cleaned = re.sub(preamble, "", cleaned, flags=re.IGNORECASE)

        abbreviations = {
            r"\bLMD\b": "Ligji për Marrëdhëniet e Detyrimeve",
            r"\bLSHT\b": "Ligji për Shoqëritë Tregtare",
            r"\bKPRK\b": "Kodi Penal i Republikës së Kosovës (Nr. 06/L-074)",
            r"\bKPPRK\b": "Kodi i Procedurës Penale të Kosovës",
            r"\bLPK\b": "Ligji për Procedurën Kontestimore",
            r"\bLFK\b": "Ligji për Familjen i Kosovës",
            r"\bPSRK\b": "Prokuroria Speciale e Republikës së Kosovës",
        }
        for abbr, expansion in abbreviations.items():
            cleaned = re.sub(abbr, f"{abbr} ({expansion})", cleaned, flags=re.IGNORECASE)

        return cleaned.strip()

    async def chat(
        self,
        query: str,
        user_id: str,
        case_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        jurisdiction: str = 'ks',
        history: Optional[List[Dict[str, Any]]] = None,
        domain: Optional[str] = 'automatic'
    ) -> AsyncGenerator[str, None]:

        current_date_str = datetime.now(timezone.utc).strftime("%d.%m.%Y")

        client_position = "PALË NË PROCEDURË"
        client_name = "Klienti / Parashtruesi"
        case_title = "Lënda Ligjore"
        db_documents = []
        case_doc = None
        c_oid = None

        if case_id and self.db is not None:
            try:
                c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
                case_doc = self.db.cases.find_one({"_id": c_oid})
                if case_doc:
                    if case_doc.get("client_position") or case_doc.get("client_role"):
                        client_position = str(case_doc.get("client_position") or case_doc.get("client_role")).upper()
                    client_name = case_doc.get("client_name") or case_doc.get("client", {}).get("name") or client_name
                    case_title = case_doc.get("title") or case_doc.get("case_name") or case_title

                doc_filter: Dict[str, Any] = {
                    "$or": [{"case_id": str(case_id)}, {"case_id": c_oid}],
                    "status": {"$ne": "DELETED"}
                }

                if document_ids and len(document_ids) > 0:
                    doc_oids = [ObjectId(did) for did in document_ids if ObjectId.is_valid(did)]
                    doc_strs = [str(did) for did in document_ids]
                    doc_filter["_id"] = {"$in": doc_oids + doc_strs}

                db_documents = list(self.db.documents.find(doc_filter).sort([("created_at", 1), ("_id", 1)]))

            except Exception as ex:
                logger.warning(f"Could not read client documents: {ex}")

        if history is None and self.db is not None and case_id and user_id:
            try:
                past_cursor = self.db[CASE_CHAT_HISTORY_COLLECTION].find({
                    "user_id": str(user_id),
                    "case_id": str(case_id)
                }).sort("created_at", -1).limit(10)

                raw_hist = list(past_cursor)
                raw_hist.reverse()

                history = []
                for h in raw_hist:
                    history.append({
                        "role": h.get("role", "user"),
                        "content": h.get("content", "")
                    })
            except Exception as e:
                logger.warning(f"Could not load case chat history: {e}")
                history = []

        single_doc_obj = db_documents[0] if (document_ids and len(document_ids) == 1 and db_documents) else None

        from app.services import vector_store_service
        query_lower = query.lower()
        optimized_query = self._optimize_query(query)
        req_pillar = detect_requested_pillar(query_lower)

        is_case_wide_request = any(kw in query_lower for kw in [
            "analizo rastin", "analizë e rastit", "analizë standarde e rastit",
            "pasqyra ekzekutive e lëndës", "pasqyra e lëndës", "raportin master",
            "autopsi e plotë", "fashikull", "gjithë fashikullit", "shkeljet", "kronologjia"
        ])

        is_statutory_verification = any(kw in query_lower for kw in [
            "verifiko nenet", "a janë të sakta nenet", "referencat ligjore",
            "baza ligjore", "nenet e ligjit", "nxirr nenet", "kontrollo nenet"
        ])

        if is_case_wide_request:
            user_intent = "COMPREHENSIVE_ANALYSIS"
            single_doc_obj = None
        elif is_statutory_verification:
            user_intent = "STATUTORY_VERIFICATION"
        else:
            user_intent = IntentDetector.detect(query)

        sample_text = ""
        if single_doc_obj:
            sample_text = (single_doc_obj.get("content") or single_doc_obj.get("extracted_text") or single_doc_obj.get("text") or "")[:10000]
        elif db_documents:
            sample_text = " ".join([(d.get("content") or d.get("extracted_text") or "")[:2000] for d in db_documents])

        detected_domain = BasePillarService.detect_case_domain(
            case_title=case_title,
            context_str=sample_text,
            manifest_str=""
        )

        exec_query = optimized_query
        system_prompt = ""

        if user_intent in ["COMPREHENSIVE_ANALYSIS", "PILLAR_STRATEGY", "PILLAR_STATUTES", "PILLAR_QUESTIONS", "PILLAR_DAMAGES"]:
            case_docs = vector_store_service.query_case_knowledge_base(
                user_id=user_id,
                query_text=optimized_query,
                case_context_id=case_id,
                document_ids=document_ids,
                n_results=35
            )
            global_docs = vector_store_service.query_global_knowledge_base(
                query_text=optimized_query, n_results=15
            )
            manifest_str, context_str = ContextBuilder.build(case_docs, global_docs, db_documents)

            system_prompt = f"""
            Ti je "Juristi AI - Asistenti Ligjor dhe Këshilltari Kryesor në Kosovë".
            LËNDA: **{case_title}** | LËMIA: **{detected_domain}** | KLIENTI: **{client_name}** ({client_position}) | DATA: {current_date_str}

            {NATURAL_COUNSEL_INSTRUCTION}

            SHKRESAT E LËNDËS ({len(db_documents)} DOKUMENTE NË FASHIKULL):
            {manifest_str}
            {context_str}
            """

        elif user_intent == "STATUTORY_VERIFICATION":
            dossier_blocks = []
            for idx, doc in enumerate(db_documents, 1):
                doc_title = doc.get("file_name") or f"Dokumenti #{idx}"
                raw_text = (doc.get("content") or doc.get("extracted_text") or "").strip()
                p_count = doc.get("page_count", "1")
                dossier_blocks.append(f"SHKRESA #{idx}: {doc_title} (Faqe: {p_count})\n{raw_text}\n")

            context_docs = "\n".join(dossier_blocks)
            base_prompt = StatutoryVerificationService.build_prompt(
                case_title=case_title,
                client_name=client_name,
                client_position=client_position,
                current_date_str=current_date_str,
                context_str=context_docs,
                manifest_str="",
                case_domain=detected_domain,
                query_text=optimized_query,
                user_id=user_id,
                case_id=case_id,
                db=self.db
            )
            system_prompt = base_prompt + "\n\n" + NATURAL_COUNSEL_INSTRUCTION

        elif user_intent == "DRAFTING":
            case_docs = vector_store_service.query_case_knowledge_base(
                user_id=user_id,
                query_text=optimized_query,
                case_context_id=case_id,
                document_ids=document_ids,
                n_results=25
            )
            global_docs = vector_store_service.query_global_knowledge_base(
                query_text=optimized_query, n_results=15
            )
            manifest_str, context_str = ContextBuilder.build(case_docs, global_docs, db_documents)

            base_prompt = LegalDraftingService.build_prompt(
                case_title=case_title,
                client_name=client_name,
                client_position=client_position,
                current_date_str=current_date_str,
                manifest_str=manifest_str,
                context_str=context_str,
                query=optimized_query,
                case_domain=detected_domain,
                db=self.db,
                user_id=user_id,
                case_id=case_id
            )
            system_prompt = base_prompt + "\n\n" + NATURAL_COUNSEL_INSTRUCTION
            exec_query = f"Harto aktin e plotë procedural të kërkuar ({optimized_query}) me strukturë solemne gjyqësore."
        else:
            case_docs = vector_store_service.query_case_knowledge_base(
                user_id=user_id,
                query_text=optimized_query,
                case_context_id=case_id,
                document_ids=document_ids,
                n_results=25
            )
            global_docs = vector_store_service.query_global_knowledge_base(
                query_text=optimized_query, n_results=15
            )
            manifest_str, context_str = ContextBuilder.build(case_docs, global_docs, db_documents)

            system_prompt = f"""
            Ti je "Juristi AI - Asistenti Ligjor dhe Këshilltari Kryesor në Kosovë".
            LËNDA: **{case_title}** | LËMIA: **{detected_domain}** | KLIENTI: **{client_name}** ({client_position}) | DATA: {current_date_str}

            {NATURAL_COUNSEL_INSTRUCTION}

            SHKRESAT E LËNDËS ({len(db_documents)} DOKUMENTE NË FASHIKULL):
            {manifest_str}
            {context_str}
            """

        if self.db is not None and case_id and user_id:
            try:
                self.db[CASE_CHAT_HISTORY_COLLECTION].insert_one({
                    "user_id": str(user_id),
                    "case_id": str(case_id),
                    "role": "user",
                    "content": query,
                    "created_at": datetime.now(timezone.utc)
                })
            except Exception as e:
                logger.warning(f"Could not save user chat message: {e}")

        full_generated_response = ""
        async for content in self.response_generator.generate_stream(
            system_prompt,
            exec_query,
            context="",
            history=history,
            model=FAST_SEARCH_MODEL,
        ):
            full_generated_response += content
            yield content

        if self.db is not None and case_id and user_id and full_generated_response.strip():
            try:
                self.db[CASE_CHAT_HISTORY_COLLECTION].insert_one({
                    "user_id": str(user_id),
                    "case_id": str(case_id),
                    "role": "assistant",
                    "content": full_generated_response.strip(),
                    "created_at": datetime.now(timezone.utc)
                })
            except Exception as e:
                logger.warning(f"Could not save assistant chat message: {e}")