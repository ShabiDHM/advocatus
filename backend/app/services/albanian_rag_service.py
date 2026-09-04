# FILE: backend/app/services/albanian_rag_service.py
# PHOENIX PROTOCOL - DYNAMIC RAG SERVICE V250.0 (FULL INTEGRAL DOSSIER SYNTHESIS • SUPREME INQUISITION)

import os
import logging
import re
from typing import List, Optional, Dict, Any, AsyncGenerator, Tuple
from datetime import datetime, timezone
from bson import ObjectId

from app.core.config import settings

# Modulet RAG
from app.services.rag.intent_detector import IntentDetector
from app.services.rag.context_builder import ContextBuilder
from app.services.rag.response_generator import ResponseGenerator
from app.services.pillars.base_pillar_service import BasePillarService

# Importimi i Shtyllave Kryesore Elitare
from app.services.pillars.forensic_audit_service import ForensicAuditService
from app.services.pillars.legal_drafting_service import LegalDraftingService
from app.services.pillars.comprehensive_analysis_service import ComprehensiveAnalysisService

logger = logging.getLogger(__name__)

MANDATORY_LEGAL_DISCLAIMER = (
    "\n\n---\n"
    "⚖️ **KLAUZOLË E PËRGJEGJËSISË LIGJORE:**\n"
    "*Kjo analizë dhe këto sugjerime procedurale janë gjeneruar nga Juristi AI për qëllime informative, "
    "kërkimore dhe mbështetjeje profesionale. Ato nuk zëvendësojnë përfaqësimin e autorizuar nga një Avokat i licencuar i "
    "Odës së Avokatëve të Kosovës (OAK). Të gjitha nenet, afatet procedurale dhe aktet duhet të verifikohen me legjislacionin "
    "pozitiv në fuqi para përdorimit zyrtar në organet e drejtësisë.*"
)

ANTI_HALLUCINATION_INSTRUCTION = """
RREGULLAT E HEKURTA TË DOKTRINËS DHE HARTIMIT:
1. CITO NENET me saktësi absolute neni-për-nen duke u mbështetur në shkresat e fashikullit dhe ligjet e Kosovës.
2. MOS shpik fakte, data apo shuma që nuk figurojnë në fashikull.
3. Përpilo dhe harto gjithmonë aktin e kërkuar procedural duke shfrytëzuar të gjitha provat e administruara në dosje.
4. Përdor ligjet pozitive të Kosovës: LPK Nr. 03/L-006, LMD Nr. 04/L-077, KPK Nr. 06/L-074, KPPRK Nr. 08/L-032, LSHT Nr. 06/L-016, Ligji për Gjykatën Komerciale Nr. 08/L-015, Ligji për PSRK Nr. 03/L-052.
"""


def is_valid_legal_report(text: str) -> bool:
    """Verifikon që përgjigja është një raport i vërtetë gjyqësor dhe JO një gabim teknik."""
    if not text or len(text.strip()) < 300:
        return False
    
    lower_text = text.lower()
    error_markers = [
        "përkohësisht i ngarkuar",
        "error code:",
        "context_length_exceeded",
        "not a valid model",
        "no endpoints found",
        "gabim teknik"
    ]
    for marker in error_markers:
        if marker in lower_text:
            return False
            
    return True


class AlbanianRAGService:
    """Shërbimi Kryesor RAG — V250.0 me Full Integral Dossier Synthesis."""

    def __init__(self, db: Any):
        self.db = db
        self.response_generator = ResponseGenerator()
        logger.info("✅ [RAG] Juristi AI Dynamic Service V250.0 Initialized.")

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
                    "$or": [{"case_id": case_id}, {"case_id": c_oid}],
                    "status": {"$ne": "DELETED"}
                }

                if document_ids and len(document_ids) > 0:
                    doc_oids = [ObjectId(did) for did in document_ids if ObjectId.is_valid(did)]
                    doc_strs = [str(did) for did in document_ids]
                    doc_filter["_id"] = {"$in": doc_oids + doc_strs}

                # Tërheqja e plotë e dokumenteve me renditje kronologjike
                db_documents = list(self.db.documents.find(doc_filter).sort([("created_at", 1), ("date", 1)]))
            except Exception as ex:
                logger.warning(f"Could not read case documents: {ex}")

        # Identifikimi i një dokumenti të vetëm nëse është përzgjedhur (Auditim i Shkresës me Peshore ⚖️)
        single_doc_obj = db_documents[0] if (document_ids and len(document_ids) == 1 and db_documents) else None

        from app.services import vector_store_service
        user_intent = IntentDetector.detect(query)
        optimized_query = self._optimize_query(query)

        # 🔒 MBROJTJA ME DRYN HEKURI:
        # Nëse thirrja ka ardhur me 1 dokument të vetëm, detyrohet FORENSIC_AUDIT
        if single_doc_obj and (
            user_intent in ["FORENSIC_AUDIT", "COMPREHENSIVE_ANALYSIS"] or
            "direktivë forenzike" in query.lower() or
            "audit" in query.lower()
        ):
            user_intent = "FORENSIC_AUDIT"

        # Zbulimi dinamik i lëmisë
        sample_text = ""
        if single_doc_obj:
            sample_text = (single_doc_obj.get("content") or single_doc_obj.get("extracted_text") or single_doc_obj.get("text") or "")[:5000]
        elif db_documents:
            sample_text = " ".join([(d.get("content") or d.get("extracted_text") or "")[:1500] for d in db_documents[:5]])

        detected_domain = BasePillarService.detect_case_domain(
            case_title=case_title,
            context_str=sample_text,
            manifest_str=""
        )

        # =========================================================================
        # ⚡ SMART CACHE CHECK (Me mbrojtje nga kthimi i analizave të vjetra)
        # =========================================================================
        is_explicit_reanalysis = any(w in query.lower() for w in ["analizo", "ri-analizo", "gjenero", "kallxim", "audit", "raport"])

        if user_intent == "COMPREHENSIVE_ANALYSIS" and case_doc and not is_explicit_reanalysis:
            is_dirty = case_doc.get("analysis_dirty", False)
            cached_analysis = case_doc.get("latest_deep_analysis") or case_doc.get("latest_comprehensive_analysis")

            if not is_dirty and is_valid_legal_report(cached_analysis):
                logger.info(f"⚡ [Smart Cache HIT] Kthehet latest_deep_analysis për lëndën {case_id}.")
                yield cached_analysis
                yield MANDATORY_LEGAL_DISCLAIMER
                return

        if user_intent == "FORENSIC_AUDIT" and single_doc_obj and not is_explicit_reanalysis:
            is_case_dirty = case_doc.get("analysis_dirty", False) if case_doc else False
            cached_doc_audit = single_doc_obj.get("latest_analysis") or single_doc_obj.get("latest_forensic_audit")
            
            if not is_case_dirty and is_valid_legal_report(cached_doc_audit):
                logger.info(f"⚡ [Smart Cache HIT] Kthehet latest_analysis për dokumentin {single_doc_obj.get('_id')}.")
                yield cached_doc_audit
                yield MANDATORY_LEGAL_DISCLAIMER
                return

        # =========================================================================
        # 🔍 NDËRTIMI I KONTEKSTIT DHE PROMPT-IT DINAMIK
        # =========================================================================
        exec_query = optimized_query
        system_prompt = ""

        DYNAMIC_SUGGESTIONS_PROMPT = """
        UDHËZIM PËR SUGJERIMET NË FUND TË PËRGJIGJES:
        Në fund të përgjigjes tënde, gjenero saktësisht 3 hapa të ardhshëm taktikë dhe konkretë që dalin drejtpërdrejt nga kjo shkresë specifike:
        Sugjerime:
        1. [Veprimi konkret i parë procedural]
        2. [Veprimi konkret i dytë]
        3. [Veprimi konkret i tretë]
        """

        if user_intent == "FORENSIC_AUDIT":
            doc_text = ""
            if single_doc_obj:
                doc_text = single_doc_obj.get("content") or single_doc_obj.get("extracted_text") or single_doc_obj.get("text") or ""
            
            if not doc_text and db_documents:
                doc_text = db_documents[0].get("content") or db_documents[0].get("extracted_text") or ""

            doc_name = single_doc_obj.get('file_name', 'Dokument Gjyqësor') if single_doc_obj else 'Dokument'
            manifest_str = f"Dokumenti në Audit: {doc_name}"
            
            base_prompt = ForensicAuditService.build_prompt(
                case_title=case_title,
                client_name=client_name,
                client_position=client_position,
                current_date_str=current_date_str,
                context_str=doc_text,
                document_text=doc_text,
                manifest_str=manifest_str,
                case_domain=detected_domain,
                db=self.db,
                user_id=user_id,
                case_id=""
            )
            system_prompt = f"{base_prompt}\n\n{DYNAMIC_SUGGESTIONS_PROMPT}"
            exec_query = f"Kryej Auditimin Suprem Forenzik të dokumentit '{doc_name}' duke nxjerrë ÇDO NEN në Tabelën e Seksionit 4 dhe duke analizuar shkeljet procedurale ekskluzivisht mbi bazën e këtij akti."

        elif user_intent in ["COMPREHENSIVE_ANALYSIS", "PILLAR_STRATEGY", "PILLAR_STATUTES", "PILLAR_QUESTIONS", "PILLAR_DAMAGES"]:
            # =========================================================================
            # 🚀 FULL INTEGRAL DOSSIER SYNTHESIS (Gëlltitja e të gjitha shkresave)
            # =========================================================================
            dossier_blocks = []
            manifest_lines = []

            for idx, doc in enumerate(db_documents, 1):
                doc_title = doc.get("file_name") or doc.get("title") or f"Dokumenti #{idx}"
                doc_text = (doc.get("content") or doc.get("extracted_text") or doc.get("text") or "").strip()
                doc_date = doc.get("document_date") or doc.get("created_at") or ""
                if hasattr(doc_date, "strftime"):
                    doc_date = doc_date.strftime("%d.%m.%Y")
                
                manifest_lines.append(f"{idx}. {doc_title} (Data/Ref: {doc_date})")
                dossier_blocks.append(
                    f"======================================================================\n"
                    f"SHKRESA #{idx} NË FASHIKULL: {doc_title} | DATA: {doc_date}\n"
                    f"======================================================================\n"
                    f"{doc_text}\n"
                )

            # Nëse kemi dokumente në bazë, përdorim fashikullin e plotë pa e cunguar me vektorë
            if dossier_blocks:
                integral_context_str = "\n".join(dossier_blocks)
                manifest_str = "\n".join(manifest_lines)
            else:
                # Fallback vetëm nëse nuk ka dokumente të ngarkuara
                case_docs = vector_store_service.query_case_knowledge_base(
                    user_id=user_id, query_text=optimized_query, case_context_id=case_id, n_results=25
                )
                global_docs = vector_store_service.query_global_knowledge_base(
                    query_text=optimized_query, n_results=15
                )
                manifest_str, integral_context_str = ContextBuilder.build(case_docs, global_docs, db_documents)

            base_prompt = ComprehensiveAnalysisService.build_prompt(
                case_title=case_title,
                client_name=client_name,
                client_position=client_position,
                current_date_str=current_date_str,
                manifest_str=manifest_str,
                context_str=integral_context_str,
                case_domain=detected_domain,
                db=self.db,
                query_text=optimized_query,
                user_id=user_id,
                case_id=case_id
            )
            system_prompt = f"{base_prompt}\n\n{DYNAMIC_SUGGESTIONS_PROMPT}"
            exec_query = (
                "Kryej Auditimin Doktrinar Suprem të plotë të këtij fashikulli. "
                "Shqyrto të gjitha shkresat, kryqëzo provat materiale me deklaratat, zbulo çdo shkelje thelbësore, "
                "identifiko përgjegjësitë e secilit aktor dhe gjenero Raportin Master të plotë në të 8 Seksionet pa asnjë shkurtim."
            )

        elif user_intent == "DRAFTING":
            case_docs = vector_store_service.query_case_knowledge_base(
                user_id=user_id, query_text=optimized_query, case_context_id=case_id, n_results=15
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
            system_prompt = f"{base_prompt}\n\n{DYNAMIC_SUGGESTIONS_PROMPT}"
            exec_query = f"Harto aktin e plotë procedural të kërkuar ({optimized_query}) me strukturë solemne gjyqësore."
        else:
            case_docs = vector_store_service.query_case_knowledge_base(
                user_id=user_id, query_text=optimized_query, case_context_id=case_id, n_results=15
            )
            global_docs = vector_store_service.query_global_knowledge_base(
                query_text=optimized_query, n_results=15
            )
            manifest_str, context_str = ContextBuilder.build(case_docs, global_docs, db_documents)

            system_prompt = f"""
            Ti je "Juristi AI - Asistenti Ligjor Inteligjent dhe Eksperti Kryesor i Doktrinës Ligjore në Kosovë".
            LËNDA: **{case_title}** | LËMIA: **{detected_domain}** | KLIENTI: **{client_name}** ({client_position}) | DATA: {current_date_str}

            {ANTI_HALLUCINATION_INSTRUCTION}

            DOKUMENTET DHE PROVAT E FASHIKULLIT:
            {manifest_str}
            {context_str}

            {DYNAMIC_SUGGESTIONS_PROMPT}
            """

        full_generated_response = ""
        async for content in self.response_generator.generate_stream(system_prompt, exec_query, context=""):
            full_generated_response += content
            yield content

        # =========================================================================
        # 💾 RUAJTJA E ANALIZËS SË RE NË MONGODB
        # =========================================================================
        if is_valid_legal_report(full_generated_response):
            if user_intent == "COMPREHENSIVE_ANALYSIS" and c_oid and self.db is not None:
                try:
                    self.db.cases.update_one(
                        {"_id": c_oid},
                        {"$set": {
                            "latest_deep_analysis": full_generated_response.strip(),
                            "latest_comprehensive_analysis": full_generated_response.strip(),
                            "analysis_dirty": False,
                            "last_analyzed_at": datetime.now(timezone.utc)
                        }}
                    )
                except Exception as save_err:
                    logger.warning(f"Could not cache case analysis: {save_err}")

            if user_intent == "FORENSIC_AUDIT" and single_doc_obj and self.db is not None:
                try:
                    self.db.documents.update_one(
                        {"_id": single_doc_obj["_id"]},
                        {"$set": {
                            "latest_analysis": full_generated_response.strip(),
                            "latest_forensic_audit": full_generated_response.strip(),
                            "last_audited_at": datetime.now(timezone.utc)
                        }}
                    )
                except Exception as save_err:
                    logger.warning(f"Could not cache doc audit: {save_err}")

        yield MANDATORY_LEGAL_DISCLAIMER