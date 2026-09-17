# FILE: backend/app/services/document_review_service.py
# PHOENIX PROTOCOL - DOCUMENT REVIEW SERVICE V1.0
# Verifikim i një dokumenti të vetëm kundrejt:
#   - Statutory Laws (Gazeta Zyrtare e Kosovës)
#   - Precedentëve të Gjykatës Supreme
# 6 seksione të dedikuara për review.

import logging
import re
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable, Set, Generator, Tuple
from collections import defaultdict
from difflib import SequenceMatcher
from bson import ObjectId

from app.services.llm.llm_client import (
    _call_llm,
    _get_sync_client,
    _prepare_system_prompt,
    _sanitize_and_disambiguate_prompt,
    _get_provider_routing_payload,
    _get_api_key,
    DEEP_ANALYSIS_MODEL,
)
from app.services.vector_store_service import query_global_knowledge_base

logger = logging.getLogger(__name__)


SYNTHESIS_COLLECTION = "case_synthesis"
EXTRACTION_COLLECTION = "case_extractions"

STREAM_BATCH_CHARS = 30
STREAM_BATCH_INTERVAL_SEC = 0.15

MAX_KB_LOOKUPS = 25              # max nene për të verifikuar në KB
PRECEDENT_SIMILARITY_THRESHOLD = 0.8
MAX_PRECEDENTS_PER_ARTICLE = 5
MAX_ARTICLE_CITATIONS = 60       # max nene për t'u nxjerrë nga dokumenti


# ────────────────────────────────────────────────────────────────────────────
# PATTERNS
# ────────────────────────────────────────────────────────────────────────────

# Neni X, Neni X.Y, Neni X/Y, Neni X i [Ligjit], Neni X i KPRK-së
ARTICLE_PATTERN = re.compile(
    r'\b(?:Neni|Nenit|Nenin|Nen[ëe]t|Artikulli|Art\.?)\s+'
    r'(\d+(?:[\.\/]\d+)*(?:\s*,\s*par\.\s*\d+(?:\s*(?:dhe|,)\s*\d+)*)?)'
    r'((?:\s+(?:i|të|te|e)\s+[A-ZËÇ][\w\d\-ëçËÇ]+(?:-[a-zëç]+)?)*)',
    re.IGNORECASE | re.UNICODE,
)

# Law name me numër: "Ligji Nr. 04/L-125", "KPPRK Nr. 08/L-032"
LAW_MENTION_PATTERN = re.compile(
    r'(?:Ligji\s+Nr\.?\s+\d+\/[A-Za-z]-\d+(?:\s+për\s+[^\n(]+?)?'
    r'|(?:KPPRK|KPRK|KPPK|LPK|LMD|LFK|LSHT)\s+Nr\.?\s+\d+\/[A-Za-z]-\d+'
    r'|KPPRK|KPRK|KPPK|LPK|LMD|LFK|LSHT|Kushtetuta)',
    re.IGNORECASE,
)

# Precedent: PML.Nr. X/Y, Rev.Nr. X/Y, etj.
CASE_NUMBER_PATTERN = re.compile(
    r'\b(?:PML|Rev|PML|ML|PA1|PKR|KMLP|ANR|PZR|CP|PN|KP|P|C|KE|CA|PP\.II)'
    r'\.?\s*[Nn]r\.?\s*\d+[/\-\d]*\b',
    re.IGNORECASE,
)

# Titull professional
TITLE_PREFIX_PATTERN = re.compile(
    r'^(?:Dr\.|Prof\.|Mr\.|Znj\.|Z\.|M\.Sc\.)\s+',
    re.IGNORECASE,
)


# ────────────────────────────────────────────────────────────────────────────
# SECTION PROMPTS — 6 seksione specifike për review dokumenti
# ────────────────────────────────────────────────────────────────────────────

DOCUMENT_REVIEW_PROMPTS = {
    "document_summary": {
        "title": "PËRMBLEDHJE E DOKUMENTIT",
        "max_tokens": 1200,
        "prompt": """Ti je "Revizor i Gjykatës Supreme" në Kosovë. Bazuar në 
digest-in, harto PËRMBLEDHJEN E DOKUMENTIT në 3-4 paragrafë.

DETYRA:
- Identifiko TIPIN e saktë të dokumentit (Aktvendim, Aktgjykim, Padi, 
  Kallëzim Penal, Kontratë, Ankesë, Kërkesë, Memo, Raport, etj.)
- Kush e ka lëshuar (gjykata, pala, institucioni)
- Data e lëshimit dhe numri i lëndës
- Palët e përfshira dhe rolet e tyre
- Objekti i dokumentit në 1-2 fjali
- Statusi aktual i dokumentit (nëse dihet: i plotfuqishëm, në apelim, etj.)

SHKRUAJ në gjuhë standarde juridike shqipe. JI KONCIS dhe i saktë.

RREGULLA:
- Përdor VETËM atë që gjendet në digest
- NUK lejohet të shpikësh emra, institucione, data""",
    },

    "article_verification": {
        "title": "VERIFIKIMI I NENEVE TË CITUARA",
        "max_tokens": 2600,
        "prompt": """Ti je "Verifikues i Neneve Ligjore" në Gjykatën Supreme të Kosovës.

Bazuar në digest-in, verifiko ÇDO NEN të cituar në dokument.

⚠️  RREGULLA STRIKTE:
- Seksioni "📖 VERIFIKIMI I NENEVE" i digest-it përmban verifikimin 
  e bërë paraprakisht për çdo nen të cituar në dokument.
- Për ÇDO nen:
    * STATUSI: EKZISTON / NUK EKZISTON
    * LIGJI I SAKTË (emri + numri)
    * PËRSHKRIMI I NENIT (nëse gjendet në bazë)
    * REFERENCAT NË DOKUMENT (ku citohet: faqe)
- NËSE neni NUK u gjet në bazën ligjore → shkruaj:
    "Neni X — NUK U GJET NË BAZËN LIGJORE"
  PA shpikje përshkrimi.
- NUK LEJOHET të shpikësh përshkrime neni.
- NUK LEJOHET të thuash "Neni X ka të bëjë me..." nëse përshkrimi nuk 
  gjendet në digest.

FORMATI PËR ÇDO NEN:

### Neni [numri] i [Ligjit]
**Statusi:** ✅ EKZISTON / ❌ NUK EKZISTON
**Përshkrimi (nga baza ligjore):** [fjalë për fjalë nga digest]
**Referohet në dokument:** [faqe/kontekst]

OSE për nene që nuk ekzistojnë:

### Neni [numri] i [Ligjit]
**Statusi:** ❌ NUK U GJET NË BAZËN LIGJORE
**Referohet në dokument:** [faqe/kontekst]
**Rekomandim:** [Të verifikohet manualisht nga juristi]

MOS përfshi introduksione. Fillo direkt me nenet.""",
    },

    "supreme_court_precedents": {
        "title": "PRECEDENTËT E GJYKATËS SUPREME",
        "max_tokens": 2800,
        "prompt": """Ti je "Analist i Precedentëve" në Gjykatën Supreme të Kosovës.

Bazuar në digest-in, analizo precedentët relevantë për këtë dokument.

⚠️  RREGULLA:
- Seksioni "🏛️ PRECEDENTËT RELEVANT" i digest-it përmban precedentë 
  të gjetur automatikisht nga baza e 1,425 faqeve të Gjykatës Supreme.
- Seksioni "📋 PRECEDENTË TË CITUAR NË DOKUMENT" përmban precedentët 
  që dokumenti VETË i citon (me numra lënde).

DETYRA:
A. PRECEDENTËT E CITUAR NË DOKUMENT (nëse ka)
   - Listoji ata që dokumenti i referon drejtpërdrejt
   - Vlerëso: a janë të saktë? a ka citation errors?

B. PRECEDENTËT E REKOMANDUAR (nga baza)
   - Listo 3-7 precedentë që Gjykata Supreme ka zbatuar për të njëjtat 
     nene ose çështje të ngjashme
   - Për secilin: numri i lëndës + konteksti
   - PSE është relevant për këtë dokument

C. REKOMANDIMI
   - Nëse dokumenti NUK citon precedentë relevantë → rekomando 
     shtimin e tyre
   - Nëse dokumenti citon precedentë → vlerëso cilësinë

FORMATI:
### A. Precedentët e cituar në dokument
- [PML.Nr. X/Y] — [konteksti]

### B. Precedentët e rekomanduar nga Gjykata Supreme
1. **[PML.Nr. X/Y]** — [konteksti] → **Relevanca:** [pse]
2. ...

### C. Rekomandimi
[2-3 fjali strategjike]

NUK LEJOHET të shpikësh numra precedentësh.""",
    },

    "drafting_quality": {
        "title": "ANALIZA E CILËSISË SË HARTIMIT",
        "max_tokens": 2200,
        "prompt": """Ti je "Revizor i Cilësisë së Akteve Gjyqësore" në Kosovë.

Bazuar në digest-in, analizo CILËSINË E HARTIMIT të dokumentit.

DETYRA:
A. STRUKTURA FORMALE
   - A ka strukturë standarde? (p.sh. hyrje, dispozitiv, arsyetim)
   - A mungon ndonjë element i nevojshëm?

B. TERMINOLOGJIA LIGJORE
   - A përdoret terminologji standarde juridike?
   - A ka terma të papërshtatshëm ose jo-zyrtarë?

C. ARSYETIMI JURIDIK
   - A ka arsyetim të qartë?
   - A mbështetet në nene të sakta?
   - A citohen faktet në mënyrë koherente?

D. KONSISTENCA
   - A ka kontradikta të brendshme?
   - A përputhet data dhe numri i lëndës në të gjithë dokumentin?

E. VLERËSIMI I PËRGJITHSHËM
   - Notë: E shkëlqyer / E mirë / Mesatare / Dobët
   - 1-2 fjali përmbledhëse

FORMATI:
## A. Struktura
- [vëzhgime]

## B. Terminologjia
- [vëzhgime]

... dhe kështu me radhë.

NUK LEJOHET të shpikësh mangësi që nuk ekzistojnë. Bazohu VETËM në digest.""",
    },

    "errors_corrections": {
        "title": "GABIME DHE KORRIGJIME",
        "max_tokens": 2600,
        "prompt": """Ti je "Revizor i Akteve Gjyqësore" me ekspertizë në korrigjimin 
e akteve juridike në Kosovë.

Bazuar në digest-in, identifiko GABIME dhe propozo KORRIGJIME.

DETYRA:
A. GABIME NË NENE
   - Nene që NUK EKZISTOJNË në bazën ligjore
   - Nene që janë cituar me numër të gabuar
   - Nene që janë atribuar ligjit të gabuar
   - PËR ÇDO GABIM → propozo korrigjimin konkret:
     "Neni X i [Ligjit] është i gabuar → Neni Y i [Ligjit]"

B. GABIME FAKTIKE
   - Data që nuk përputhen
   - Numra lënde të gabuar
   - Emra të shkruar gabim
   - Referenca të brendshme të pasakta

C. GABIME PROCEDURALE
   - Shkelje të procedurës
   - Afate të tejkaluara
   - Elemente që mungojnë

D. KORRIGJIME TË REKOMANDUARA
   - Për secilin gabim, jep KORRIGJIMIN konkret
   - Përshkruaj IMPAKTIN (i vogël / i mesëm / kritik)

FORMATI:
### A. Gabime në nene
1. ❌ **Neni X i [Ligjit]** nuk ekziston → zëvendëso me 
   **Neni Y i [Ligjit]** *(impakti: kritik)*
2. ...

### B. Gabime faktike
...

NËSE NUK KA GABIME → shkruaj "Nuk u identifikuan gabime në këtë kategori."
NUK LEJOHET të shpikësh gabime.""",
    },

    "action_steps": {
        "title": "HAPAT KONKRET TË VEPRIMIT",
        "max_tokens": 2400,
        "prompt": """Ti je "Strateg i Lartë Ligjor" në Kosovë. Klienti ka marrë 
analizën e dokumentit dhe tani kërkon HAPAT KONKRET.

Bazuar në digest-in dhe analizën e mëparshme, harto PLANIN E VEPRIMIT.

DETYRA:
A. VLERËSIMI I SITUATËS
   - A duhet të ndryshohet dokumenti? (nëse ka gabime)
   - A duhet të plotësohet? (nëse mungon diçka)
   - A duhet të anulohet? (nëse është i paligjshëm)

B. HAPAT E MENJËHERSHËM (brenda 1-7 ditësh)
   1. [Veprimi konkret] — [afati] — [pse]
   2. ...

C. HAPAT AFATGJATË (1-3 muaj)
   1. [Veprimi] — [afati] — [pse]
   2. ...

D. MUNDËSITË PROCEDURALE
   - Ankesë? Në cilin organ? Afati?
   - Revizion? Afati?
   - Kthim në afat? Nëse ka bazë?
   - Mjete të tjera juridike?

E. RREZIQET
   - Çfarë mund të shkojë keq nëse nuk veprohet?
   - Çfarë humbet klienti?

FORMATI:
## A. Vlerësimi
[2-3 fjali]

## B. Hapat e menjëhershëm
1. ...

## C. Hapat afatgjatë
1. ...

## D. Mundësitë procedurale
...

## E. Rreziqet
...

NËSE dokumenti është i saktë dhe nuk ka gabime → 
përsëri jep rekomandime strategjike (ndoshta dokumenti 
është gati për tu dorëzuar).

NUK LEJOHET të shpikësh afate që nuk janë në ligj.""",
    },
}


# ────────────────────────────────────────────────────────────────────────────
# SYNC STREAMING
# ────────────────────────────────────────────────────────────────────────────

def _stream_section_sync(system_prompt, user_content, temperature=0.1):
    if not _get_api_key():
        return
    full_sys = _prepare_system_prompt(system_prompt)
    sanitized = _sanitize_and_disambiguate_prompt(user_content)
    client = _get_sync_client()
    try:
        stream = client.chat.completions.create(
            model=DEEP_ANALYSIS_MODEL,
            messages=[
                {"role": "system", "content": full_sys},
                {"role": "user", "content": sanitized},
            ],
            temperature=temperature,
            max_tokens=8192,
            stream=True,
            extra_body=_get_provider_routing_payload(),
        )
        for chunk in stream:
            if not chunk or not hasattr(chunk, "choices") or not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta and getattr(delta, "content", None):
                yield delta.content
    except Exception as e:
        logger.error(f"❌ [DOC_REVIEW] Sync streaming error: {e}")
        raise


# ────────────────────────────────────────────────────────────────────────────
# SERVICE
# ────────────────────────────────────────────────────────────────────────────

class DocumentReviewService:
    """
    Verifikim i një dokumenti të vetëm:
    - Nenet e cituara → kundrejt Gazetës Zyrtare
    - Precedentët → kundrejt Gjykatës Supreme (150+ faqe)
    - 6 seksione të dedikuara
    """

    def __init__(self, db):
        self.db = db

    # ────────────────────────────────────────────────────────────────────
    # PUBLIC — review
    # ────────────────────────────────────────────────────────────────────

    def review(
        self,
        case_id: str,
        user_id: str,
        document_id: str,
        progress_callback: Optional[Callable] = None,
        section_stream_callback: Optional[Callable[[str, str], None]] = None,
    ) -> Dict[str, Any]:
        start = time.time()

        # 1. Ngarko dokumentin + extraction
        document = self._load_document(case_id, document_id)
        extraction = self._load_extraction(case_id, document_id)

        if not document and not extraction:
            return self._empty_result(case_id, document_id, "Document not found.")

        doc_text = (
            (extraction or {}).get("text")  # nga extraction nuk ka text, do marrim nga dokumenti
            or document.get("content")
            or document.get("extracted_text")
            or document.get("text")
            or ""
        )

        if not doc_text.strip():
            return self._empty_result(
                case_id, document_id, "Document has no text content."
            )

        document_type = (
            (extraction or {}).get("document_type")
            or document.get("document_type")
            or "Dokument"
        )
        file_name = document.get("file_name", "Dokument")

        logger.info(
            f"🔍 [DOC_REVIEW] Starting: doc={document_id}, "
            f"file={file_name}, type={document_type}, "
            f"len={len(doc_text)} chars"
        )

        # 2. Nxirr nenet e cituara
        article_citations = self._extract_article_citations(doc_text)
        logger.info(
            f"📖 [DOC_REVIEW] Found {len(article_citations)} article citations"
        )

        # 3. Verifiko nenet kundrejt KB
        if progress_callback:
            try:
                progress_callback("section_started", {
                    "section_key": "kb_verification",
                    "section_title": "Duke verifikuar nenet në bazën ligjore...",
                })
            except Exception:
                pass

        article_verifications = self._verify_articles_against_kb(
            article_citations
        )

        # 4. Nxirr precedentët e cituar në dokument
        cited_precedents = self._extract_cited_precedents(doc_text)
        logger.info(
            f"🏛️ [DOC_REVIEW] Found {len(cited_precedents)} cited precedents"
        )

        # 5. Gjej precedentët e rekomanduar (similarity >0.8)
        if progress_callback:
            try:
                progress_callback("section_started", {
                    "section_key": "precedent_search",
                    "section_title": "Duke kërkuar precedentë në Gjykatën Supreme...",
                })
            except Exception:
                pass

        recommended_precedents = self._find_recommended_precedents(
            doc_text, article_citations, cited_precedents
        )

        # 6. Ndërto digest
        digest = self._build_review_digest(
            document=document,
            extraction=extraction,
            document_type=document_type,
            file_name=file_name,
            article_citations=article_citations,
            article_verifications=article_verifications,
            cited_precedents=cited_precedents,
            recommended_precedents=recommended_precedents,
        )

        logger.info(
            f"🔍 [DOC_REVIEW] Digest built: {len(digest)} chars, "
            f"articles_verified={len(article_verifications)}, "
            f"precedents_recommended={len(recommended_precedents)}"
        )

        # 7. Gjenero 6 seksionet
        sections: Dict[str, Any] = {}
        section_stats: Dict[str, Any] = {}

        for section_key, section_cfg in DOCUMENT_REVIEW_PROMPTS.items():
            section_start = time.time()
            section_title = section_cfg["title"]

            if progress_callback:
                try:
                    progress_callback("section_started", {
                        "section_key": section_key,
                        "section_title": section_title,
                    })
                except Exception:
                    pass

            try:
                content = self._synthesize_section_streaming(
                    section_key=section_key,
                    section_cfg=section_cfg,
                    digest=digest,
                    file_name=file_name,
                    document_type=document_type,
                    stream_callback=section_stream_callback,
                )

                sections[section_key] = {
                    "title": section_title,
                    "content": content,
                }
                section_stats[section_key] = {
                    "duration_sec": round(time.time() - section_start, 2),
                    "content_length": len(content),
                }

                if progress_callback:
                    try:
                        progress_callback("section_completed", {
                            "section_key": section_key,
                            "section_title": section_title,
                            "content_length": len(content),
                        })
                    except Exception:
                        pass

            except Exception as e:
                logger.error(
                    f"❌ [DOC_REVIEW] Section {section_key} failed: {e}"
                )
                sections[section_key] = {
                    "title": section_title,
                    "content": "",
                    "error": str(e),
                }
                section_stats[section_key] = {
                    "duration_sec": round(time.time() - section_start, 2),
                    "error": str(e),
                }

        duration = round(time.time() - start, 2)

        result = {
            "case_id": case_id,
            "document_id": document_id,
            "scope": "document",
            "document_ids": [document_id],
            "document_type": document_type,
            "file_name": file_name,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "sections": sections,
            "stats": {
                "case_id": case_id,
                "scope": "document",
                "document_id": document_id,
                "file_name": file_name,
                "document_type": document_type,
                "text_length": len(doc_text),
                "article_citations": len(article_citations),
                "articles_verified": len(article_verifications),
                "articles_not_found": sum(
                    1 for v in article_verifications.values()
                    if not v.get("found_in_kb")
                ),
                "cited_precedents": len(cited_precedents),
                "recommended_precedents": len(recommended_precedents),
                "digest_chars": len(digest),
                "sections_generated": len(
                    [s for s in sections.values() if s.get("content")]
                ),
                "sections_total": len(DOCUMENT_REVIEW_PROMPTS),
                "duration_sec": duration,
            },
            "verification_details": {
                "article_verifications": article_verifications,
                "cited_precedents": cited_precedents,
                "recommended_precedents": recommended_precedents,
            },
            "section_stats": section_stats,
            "status": "completed",
        }

        self._persist(result)

        logger.info(
            f"✅ [DOC_REVIEW] Complete: doc={document_id}, "
            f"sections={result['stats']['sections_generated']}/"
            f"{result['stats']['sections_total']}, "
            f"duration={duration}s"
        )

        return result

    # ────────────────────────────────────────────────────────────────────
    # LOADERS
    # ────────────────────────────────────────────────────────────────────

    def _load_document(self, case_id: str, document_id: str) -> Dict[str, Any]:
        try:
            case_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
            doc_oid = ObjectId(document_id) if ObjectId.is_valid(document_id) else document_id

            doc = self.db.documents.find_one({
                "_id": doc_oid,
                "$or": [
                    {"case_id": case_id},
                    {"case_id": case_oid},
                    {"case_id": str(case_oid)},
                ],
            })
            return doc or {}
        except Exception as e:
            logger.warning(f"⚠️ [DOC_REVIEW] load_document failed: {e}")
            return {}

    def _load_extraction(self, case_id: str, document_id: str) -> Optional[Dict[str, Any]]:
        try:
            doc = self.db[EXTRACTION_COLLECTION].find_one({
                "case_id": str(case_id),
                "document_id": str(document_id),
                "status": "completed",
            })
            return doc
        except Exception as e:
            logger.warning(f"⚠️ [DOC_REVIEW] load_extraction failed: {e}")
            return None

    # ────────────────────────────────────────────────────────────────────
    # ARTICLE EXTRACTION
    # ────────────────────────────────────────────────────────────────────

    def _extract_article_citations(self, text: str) -> List[Dict[str, Any]]:
        """
        Nxjerr të gjitha nenet e cituara në tekst.
        Kthen listë me: {article_number, law_hint, context}
        """
        if not text:
            return []

        citations: List[Dict[str, Any]] = []
        seen: Set[Tuple[str, str]] = set()

        for match in ARTICLE_PATTERN.finditer(text):
            article_number = match.group(1).strip()
            law_hint = (match.group(2) or "").strip()

            # Pastro law_hint
            if law_hint:
                # "i KPRK-së" → "KPRK"
                law_hint = re.sub(
                    r'^\s*(?:i|të|te|e)\s+',
                    '',
                    law_hint,
                    flags=re.IGNORECASE,
                ).strip()

            key = (article_number, law_hint.lower())
            if key in seen:
                continue
            seen.add(key)

            # Konteksti (100 chars)
            ctx_start = max(0, match.start() - 50)
            ctx_end = min(len(text), match.end() + 150)
            context = text[ctx_start:ctx_end].strip()

            citations.append({
                "article_number": article_number,
                "law_hint": law_hint,
                "context": context[:250],
            })

            if len(citations) >= MAX_ARTICLE_CITATIONS:
                break

        return citations

    # ────────────────────────────────────────────────────────────────────
    # ARTICLE VERIFICATION
    # ────────────────────────────────────────────────────────────────────

    def _verify_articles_against_kb(
        self, citations: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Për çdo nen të cituar, kërkon në KB dhe kthen statusin.
        Returns: {citation_key: {found_in_kb, kb_entry, description}}
        """
        verifications: Dict[str, Dict[str, Any]] = {}

        # Kufizo numrin e kërkimeve për performance
        citations_to_check = citations[:MAX_KB_LOOKUPS]

        for i, citation in enumerate(citations_to_check):
            article_num = citation["article_number"]
            law_hint = citation["law_hint"]

            # Krijo query për KB
            query = f"Neni {article_num}"
            if law_hint:
                query += f" i {law_hint}"

            try:
                kb_results = query_global_knowledge_base(query, n_results=5)
            except Exception as e:
                logger.warning(
                    f"⚠️ [DOC_REVIEW] KB query failed for {query}: {e}"
                )
                kb_results = []

            # Klasifiko rezultatet
            statute_matches = []
            precedent_matches = []

            for r in kb_results:
                src = (r.get("source") or "").lower()
                txt = (r.get("text") or "").lower()

                # Kontrollo a është statute
                is_statute = (
                    "baza statutore" in src
                    or "neni" in src
                )
                # Kontrollo a është precedent
                is_precedent = (
                    "precedent" in src
                    or "gjykatës supreme" in src
                    or "gjykatës sup" in src
                )

                # Kontrollo match me numrin e nenit
                article_pattern = re.compile(
                    rf'\bneni\s+{re.escape(article_num)}\b',
                    re.IGNORECASE,
                )

                if is_statute and article_pattern.search(txt):
                    statute_matches.append(r)
                elif is_precedent:
                    # Precedent — kontrollo a përmend nenin
                    if article_pattern.search(txt):
                        precedent_matches.append(r)
                    elif law_hint and law_hint.lower() in txt:
                        precedent_matches.append(r)

            # Vendos statusin
            found = len(statute_matches) > 0
            verification = {
                "article_number": article_num,
                "law_hint": law_hint,
                "query": query,
                "found_in_kb": found,
                "statute_match": statute_matches[0] if statute_matches else None,
                "precedent_matches": precedent_matches[:MAX_PRECEDENTS_PER_ARTICLE],
                "context": citation.get("context", ""),
            }

            key = f"Neni {article_num}"
            if law_hint:
                key += f" i {law_hint}"

            verifications[key] = verification

            if found:
                logger.info(
                    f"✅ [DOC_REVIEW] Neni {article_num} u gjet në KB "
                    f"(statute: {len(statute_matches)}, "
                    f"precedents: {len(precedent_matches)})"
                )
            else:
                logger.info(
                    f"❌ [DOC_REVIEW] Neni {article_num} NUK u gjet në KB"
                )

        return verifications

    # ────────────────────────────────────────────────────────────────────
    # PRECEDENT EXTRACTION
    # ────────────────────────────────────────────────────────────────────

    def _extract_cited_precedents(self, text: str) -> List[str]:
        """Nxjerr numrat e lëndëve të cituara në dokument."""
        if not text:
            return []

        matches = CASE_NUMBER_PATTERN.findall(text)
        # Normalizo dhe dedupe
        seen = set()
        result = []
        for m in matches:
            m_clean = re.sub(r'\s+', ' ', m.strip())
            if m_clean.lower() not in seen:
                seen.add(m_clean.lower())
                result.append(m_clean)

        return result

    # ────────────────────────────────────────────────────────────────────
    # RECOMMENDED PRECEDENTS
    # ────────────────────────────────────────────────────────────────────

    def _find_recommended_precedents(
        self,
        doc_text: str,
        citations: List[Dict[str, Any]],
        cited_precedents: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Gjen precedentë të rekomanduar me similarity >0.8.
        Përjashton ata të cituar tashmë në dokument.
        """
        recommended: Dict[str, Dict[str, Any]] = {}
        cited_lower = {c.lower() for c in cited_precedents}

        # Kërko precedents nga disa nene kyçe (max 5 nene)
        for citation in citations[:5]:
            article_num = citation["article_number"]
            law_hint = citation["law_hint"]

            query = f"precedent Gjykata Supreme për Neni {article_num}"
            if law_hint:
                query += f" i {law_hint}"

            try:
                results = query_global_knowledge_base(query, n_results=10)
            except Exception as e:
                logger.warning(
                    f"⚠️ [DOC_REVIEW] precedent search failed: {e}"
                )
                continue

            for r in results:
                src = (r.get("source") or "")
                if "precedent" not in src.lower() and "gjykatës supreme" not in src.lower():
                    continue

                case_number = r.get("case_number", "").strip()
                if not case_number:
                    continue

                case_lower = case_number.lower()
                # Skip nëse tashmë i cituar në dokument
                if case_lower in cited_lower:
                    continue

                # Skip nëse tashmë i rekomanduar
                if case_lower in recommended:
                    continue

                # Vlerëso similarity
                similarity = self._compute_similarity(
                    doc_text[:2000],
                    (r.get("text") or "")[:2000],
                )

                if similarity < PRECEDENT_SIMILARITY_THRESHOLD:
                    continue

                recommended[case_lower] = {
                    "case_number": case_number,
                    "source": src,
                    "text_snippet": (r.get("text") or "")[:500],
                    "similarity": round(similarity, 3),
                    "for_article": f"Neni {article_num}" + (
                        f" i {law_hint}" if law_hint else ""
                    ),
                }

        # Sorto sipas similarity
        sorted_recommended = sorted(
            recommended.values(),
            key=lambda x: x["similarity"],
            reverse=True,
        )

        return sorted_recommended[:10]

    def _compute_similarity(self, text_a: str, text_b: str) -> float:
        """Similarity using SequenceMatcher."""
        if not text_a or not text_b:
            return 0.0
        return SequenceMatcher(None, text_a, text_b).ratio()

    # ────────────────────────────────────────────────────────────────────
    # DIGEST
    # ────────────────────────────────────────────────────────────────────

    def _build_review_digest(
        self,
        document: Dict[str, Any],
        extraction: Optional[Dict[str, Any]],
        document_type: str,
        file_name: str,
        article_citations: List[Dict[str, Any]],
        article_verifications: Dict[str, Dict[str, Any]],
        cited_precedents: List[str],
        recommended_precedents: List[Dict[str, Any]],
    ) -> str:
        lines = []

        # ═══ 1. DOKUMENTI ═══
        lines.append("=" * 70)
        lines.append("DOKUMENTI NË REVIEW")
        lines.append("=" * 70)
        lines.append(f"Emri: {file_name}")
        lines.append(f"Lloji: {document_type}")
        lines.append(
            f"Data e dokumentit: {document.get('created_at', 'N/A')}"
        )
        lines.append(
            f"Madhësia: {len(document.get('content') or document.get('extracted_text') or '')} chars"
        )
        lines.append("")

        # ═══ 2. PËRMBLEDHJE E SHKURTËR E DOKUMENTIT ═══
        doc_text = (
            document.get("content")
            or document.get("extracted_text")
            or document.get("text")
            or ""
        )

        if doc_text:
            # Marrim fillimin e dokumentit për kontekst
            excerpt = doc_text[:3000]
            lines.append("=" * 70)
            lines.append("FILLIMI I DOKUMENTIT (për kontekst)")
            lines.append("=" * 70)
            lines.append(excerpt)
            lines.append("")

        # ═══ 3. VERIFIKIMI I NENEVE ═══
        if article_verifications:
            lines.append("=" * 70)
            lines.append("📖 VERIFIKIMI I NENEVE (kundrejt bazës ligjore)")
            lines.append("=" * 70)
            lines.append(
                f"Gjithsej {len(article_verifications)} nene të verifikuara."
            )
            lines.append(
                "KUR citon një nen në raport, përdor EKZAKTËSISHT "
                "përshkrimin e dhënë këtu. NËSE neni nuk u gjet, "
                "NJOFTONI që nuk u gjet."
            )
            lines.append("")

            for key, v in article_verifications.items():
                article_num = v["article_number"]
                law_hint = v["law_hint"]
                found = v["found_in_kb"]

                lines.append(f"**{key}:**")
                if found:
                    statute = v.get("statute_match") or {}
                    src = statute.get("source", "")
                    txt = (statute.get("text") or "")[:300]
                    lines.append(f"  STATUSI: ✅ EKZISTON")
                    lines.append(f"  Burimi: {src}")
                    lines.append(f"  Përshkrimi: {txt}")
                else:
                    lines.append(f"  STATUSI: ❌ NUK U GJET NË BAZËN LIGJORE")

                # Precedentët për këtë nen
                precedents = v.get("precedent_matches") or []
                if precedents:
                    lines.append(f"  Precedentë të gjetur:")
                    for p in precedents[:3]:
                        cn = p.get("case_number", "?")
                        lines.append(f"    • {cn}")

                lines.append("")
        else:
            lines.append("=" * 70)
            lines.append("📖 VERIFIKIMI I NENEVE")
            lines.append("=" * 70)
            lines.append(
                "NUK U IDENTIFIKUAN nene të cituara në këtë dokument."
            )
            lines.append("")

        # ═══ 4. PRECEDENTË TË CITUAR NË DOKUMENT ═══
        lines.append("=" * 70)
        lines.append("📋 PRECEDENTË TË CITUAR NË DOKUMENT")
        lines.append("=" * 70)
        if cited_precedents:
            for cn in cited_precedents:
                lines.append(f"  • {cn}")
        else:
            lines.append("  (asnjë precedent i cituar në dokument)")
        lines.append("")

        # ═══ 5. PRECEDENTË TË REKOMANDUAR ═══
        lines.append("=" * 70)
        lines.append("🏛️ PRECEDENTË TË REKOMANDUAR NGA GJYKATA SUPREME")
        lines.append("=" * 70)
        if recommended_precedents:
            lines.append(
                f"U gjetën {len(recommended_precedents)} precedentë relevantë "
                f"(similarity > {PRECEDENT_SIMILARITY_THRESHOLD})."
            )
            lines.append("")
            for p in recommended_precedents:
                lines.append(
                    f"  • {p['case_number']} (similarity: {p['similarity']})"
                )
                lines.append(f"    Për: {p['for_article']}")
                lines.append(f"    Konteksti: {p['text_snippet'][:200]}")
                lines.append("")
        else:
            lines.append(
                "NUK U GJETËN precedentë me similarity > 0.8. "
                "Nuk ka rekomandime."
            )
            lines.append("")

        # ═══ 6. METAINFO ═══
        extraction_meta = (extraction or {}).get("metadata") or {}
        if extraction_meta:
            lines.append("=" * 70)
            lines.append("METADATA E DOKUMENTIT (nga NER)")
            lines.append("=" * 70)
            for k, val in extraction_meta.items():
                if val in (None, "", [], {}):
                    continue
                lines.append(f"  {k}: {str(val)[:200]}")
            lines.append("")

        digest = "\n".join(lines)
        return digest

    # ────────────────────────────────────────────────────────────────────
    # SECTION STREAMING
    # ────────────────────────────────────────────────────────────────────

    def _synthesize_section_streaming(
        self,
        section_key: str,
        section_cfg: Dict[str, Any],
        digest: str,
        file_name: str,
        document_type: str,
        stream_callback: Optional[Callable[[str, str], None]] = None,
    ) -> str:
        system_prompt = f"""Ti je "Revizor i Gjykatës Supreme të Kosovës".

DOKUMENTI: {file_name}
LLOJI: {document_type}

{section_cfg['prompt']}

FORMATIMI:
- Përdor markdown me tituj (##, ###).
- Përfshi referenca specifike (neni, ligji, faqe, datë).
- Shkruaj në shqip standarde juridike.
- Mos shpik — bazohu VETËM në digest.
"""

        user_content = f"""DIGEST I DOKUMENTIT:

{digest}

───────────────────────────────────────────────────────

DETYRA: Harto seksionin "{section_cfg['title']}"."""

        accumulated = ""
        buffer = ""
        last_emit = time.time()
        stream_succeeded = False

        try:
            for chunk in _stream_section_sync(
                system_prompt, user_content, temperature=0.1
            ):
                stream_succeeded = True
                accumulated += chunk
                buffer += chunk

                now = time.time()
                if (
                    len(buffer) >= STREAM_BATCH_CHARS
                    or (now - last_emit) >= STREAM_BATCH_INTERVAL_SEC
                ):
                    if stream_callback and buffer:
                        try:
                            stream_callback(section_key, buffer)
                        except Exception as e:
                            logger.warning(f"⚠️ stream_callback failed: {e}")
                    buffer = ""
                    last_emit = now

            if buffer and stream_callback:
                try:
                    stream_callback(section_key, buffer)
                except Exception as e:
                    logger.warning(f"⚠️ stream_callback (flush) failed: {e}")

            return accumulated

        except Exception as e:
            logger.warning(
                f"⚠️ [DOC_REVIEW] Streaming failed for {section_key}, "
                f"falling back: {e}"
            )

            if not stream_succeeded and not accumulated:
                try:
                    raw = _call_llm(
                        system_prompt=system_prompt,
                        user_content=user_content,
                        json_mode=False,
                        temperature=0.1,
                        model=DEEP_ANALYSIS_MODEL,
                    )
                    accumulated = raw or ""
                    if stream_callback and accumulated:
                        try:
                            stream_callback(section_key, accumulated)
                        except Exception as e2:
                            logger.warning(
                                f"⚠️ stream_callback (fallback) failed: {e2}"
                            )
                except Exception as e2:
                    logger.error(f"❌ [DOC_REVIEW] Fallback failed: {e2}")
                    raise

            return accumulated

    # ────────────────────────────────────────────────────────────────────
    # PERSIST
    # ────────────────────────────────────────────────────────────────────

    def _persist(self, result: Dict[str, Any]) -> None:
        """Ruajtja në case_synthesis me scope=document."""
        try:
            self.db[SYNTHESIS_COLLECTION].update_one(
                {
                    "case_id": result["case_id"],
                    "scope": "document",
                    "document_ids": result["document_ids"],
                },
                {"$set": result},
                upsert=True,
            )
        except Exception as e:
            logger.error(f"❌ [DOC_REVIEW] Persist failed: {e}")
            raise

    def _empty_result(
        self, case_id: str, document_id: str, reason: str
    ) -> Dict[str, Any]:
        return {
            "case_id": case_id,
            "document_id": document_id,
            "scope": "document",
            "document_ids": [document_id],
            "built_at": datetime.now(timezone.utc).isoformat(),
            "sections": {},
            "stats": {
                "case_id": case_id,
                "document_id": document_id,
                "sections_generated": 0,
                "sections_total": len(DOCUMENT_REVIEW_PROMPTS),
                "duration_sec": 0.0,
            },
            "status": "empty",
            "warning": reason,
        }


# ────────────────────────────────────────────────────────────────────────────
# FACTORY
# ────────────────────────────────────────────────────────────────────────────

def get_document_review_service(db) -> DocumentReviewService:
    return DocumentReviewService(db)