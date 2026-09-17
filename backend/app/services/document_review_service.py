# FILE: backend/app/services/document_review_service.py
# PHOENIX PROTOCOL - DOCUMENT REVIEW SERVICE V2.0
# V2.0: Shtuar 4 guardrails anti-halucinacion:
#   - Guardrail #1: Prompt i rreptë për verifikim citimesh
#   - Guardrail #2: Regex ekstraktim i citimeve para LLM
#   - Guardrail #3: Verifikim i dyfishtë (LLM + LLM correction)
#   - Guardrail #4: Citation checker fjalë-për-fjalë
#   - Kthim te FAST_SEARCH_MODEL (GPT-4o-mini)

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
    FAST_SEARCH_MODEL,
)
from app.services.vector_store_service import query_global_knowledge_base

logger = logging.getLogger(__name__)


SYNTHESIS_COLLECTION = "case_synthesis"
EXTRACTION_COLLECTION = "case_extractions"

STREAM_BATCH_CHARS = 30
STREAM_BATCH_INTERVAL_SEC = 0.15

MAX_KB_LOOKUPS = 25
PRECEDENT_SIMILARITY_THRESHOLD = 0.8
MAX_PRECEDENTS_PER_ARTICLE = 5
MAX_ARTICLE_CITATIONS = 60


# ────────────────────────────────────────────────────────────────────────────
# PATTERNS
# ────────────────────────────────────────────────────────────────────────────

ARTICLE_PATTERN = re.compile(
    r'\b(?:Neni|Nenit|Nenin|Nen[ëe]t|Artikulli|Art\.?)\s+'
    r'(\d+(?:[\.\/]\d+)*(?:\s*,\s*par\.\s*\d+(?:\s*(?:dhe|,)\s*\d+)*)?)'
    r'((?:\s+(?:i|të|te|e)\s+[A-ZËÇ][\w\d\-ëçËÇ]+(?:-[a-zëç]+)?)*)',
    re.IGNORECASE | re.UNICODE,
)

LAW_MENTION_PATTERN = re.compile(
    r'(?:Ligji\s+Nr\.?\s+\d+\/[A-Za-z]-\d+(?:\s+për\s+[^\n(]+?)?'
    r'|(?:KPPRK|KPRK|KPPK|LPK|LMD|LFK|LSHT|LMDHF)\s+Nr\.?\s+\d+\/[A-Za-z]-\d+'
    r'|KPPRK|KPRK|KPPK|LPK|LMD|LFK|LSHT|LMDHF|Kushtetuta)',
    re.IGNORECASE,
)

CASE_NUMBER_PATTERN = re.compile(
    r'\b(?:PML|Rev|PML|ML|PA1|PKR|KMLP|ANR|PZR|CP|PN|KP|P|C|KE|CA|PP\.II)'
    r'\.?\s*[Nn]r\.?\s*\d+[/\-\d]*\b',
    re.IGNORECASE,
)

TITLE_PREFIX_PATTERN = re.compile(
    r'^(?:Dr\.|Prof\.|Mr\.|Znj\.|Z\.|M\.Sc\.)\s+',
    re.IGNORECASE,
)

# ═══════════════════════════════════════════════════════════════════════════
# GUARDRAIL #2: Regex për ekstraktimin deterministik të citimeve
# ═══════════════════════════════════════════════════════════════════════════

LAW_NUMBER_PATTERN = re.compile(
    r'\b(\d{2}\s*\/\s*[A-Za-z]\s*-\s*\d{2,4})\b',
    re.IGNORECASE,
)

LAW_ABBREVIATION_PATTERN = re.compile(
    r'\b(KPPRK|KPRK|KPPK|LPK|LMD|LFK|LSHT|LMDHF|Kushtetuta)\b',
    re.IGNORECASE,
)

VERIFIED_ARTICLE_PATTERN = re.compile(
    r'\bNen(?:i|it|in|ët)\s+(\d+(?:[\.\/]\d+)*)'
    r'(?:\s*,?\s*par(?:\.|agrafi|agrafit)?\s*(\d+))?',
    re.IGNORECASE | re.UNICODE,
)


def _extract_verified_citations(text: str) -> Dict[str, Any]:
    """
    GUARDRAIL #2: Ekstraktim deterministik i citimeve me regex.
    Krijon listë të mbyllur që LLM-ja NUK mund të shkelë.
    """
    if not text:
        return {
            "laws": [],
            "articles": [],
            "total_laws": 0,
            "total_articles": 0,
        }

    laws: Set[str] = set()

    # Ligjet me numër: 03/L-182, 06/L-006
    for match in LAW_NUMBER_PATTERN.finditer(text):
        law_num = match.group(1).replace(" ", "")
        laws.add(law_num)

    # Abbreviations
    for match in LAW_ABBREVIATION_PATTERN.finditer(text):
        abbr = match.group(1)
        if abbr.lower() == "kushtetuta":
            laws.add("Kushtetuta")
        else:
            laws.add(abbr.upper())

    # Nenet me kontekst
    articles: List[Dict[str, Any]] = []
    seen_articles: Set[Tuple[str, Optional[str]]] = set()

    for match in VERIFIED_ARTICLE_PATTERN.finditer(text):
        article_num = match.group(1).strip()
        paragraph = match.group(2)
        key = (article_num, paragraph)
        if key in seen_articles:
            continue
        seen_articles.add(key)
        articles.append({
            "number": article_num,
            "paragraph": paragraph,
            "raw": match.group(0).strip(),
        })

    return {
        "laws": sorted(laws),
        "articles": articles,
        "total_laws": len(laws),
        "total_articles": len(articles),
    }


# ────────────────────────────────────────────────────────────────────────────
# SECTION PROMPTS
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

⚠️ RREGULLA ABSOLUTE (GUARDRAIL #1 — NUK SHKELEN):

1. LEXO ME VËMENDJE SEKSIONIN "CITIMET E VËRTETUARA NGA DOKUMENTI (REGEX)" 
   në digest. Ky është ekstraktim DETERMINISTIK me regex — i vetmi burim i 
   së vërtetës për atë që citohet në dokument.

2. PËRDOR VETËM LIGJET DHE NENET QË SHFAQEN NË ATË SEKSION:
   - NËSE një ligj nuk është aty → NUK EKZISTON në dokument → NUK E PËRDOR
   - NËSE një nen nuk është aty → NUK EKZISTON në dokument → NUK E PËRDOR
   - NUK LEJOHET të shtosh ligje/nene që "mendon" se ekzistojnë

3. RREGULL I VEÇANTË PËR NUMRAT E LIGJEVE:
   - Nëse digest-i thotë "03/L-182", NUK mund të shkruash "06/L-006"
   - Ky është HALUDINACION i rëndë — konsiderohet gabim kritik
   - Numri i ligjit KOPJO fjalë-për-fjalë nga digest-i

4. STATUSI I ÇDO NENI:
   - ✅ EKZISTON → vetëm nëse neni është në digest
   - ❌ NUK EKZISTON → nëse neni NUK është në digest

5. FORMATI I S AKTË PËR ÇDO NEN:

### Neni [numri] i [Ligji i saktë nga digest]
**Statusi:** ✅ EKZISTON / ❌ NUK U GJET NË DOKUMENT
**Përshkrimi:** [fjalë për fjalë nga KB nëse ekziston]
**Referohet në dokument:** [kontekst nga digest]

6. NËSE NUK KA NENE TË CITUARA fare:
   - Shkruaj: "Dokumenti nuk përmban citime nene."

⚠️ ÇDO LIGJ APO NEN QË NUK SHFAQET NË SEKSIONIN "CITIMET E VËRTETUARA" 
   KONSIDEROHET HALUDINACION DHE ZBRET AUTOMATIKISHT NGA GUARDRAIL #4.

MOS përfshi introduksione. Fillo direkt me nenet.""",
    },

    "supreme_court_precedents": {
        "title": "PRECEDENTËT E GJYKATËS SUPREME",
        "max_tokens": 2800,
        "prompt": """Ti je "Analist i Precedentëve" në Gjykatën Supreme të Kosovës.

Bazuar në digest-in, analizo precedentët relevantë për këtë dokument.

⚠️ RREGULLA:
- Seksioni "🏛️ PRECEDENTË TË REKOMANDUAR" i digest-it përmban precedentë 
  të gjetur automatikisht nga baza e Gjykatës Supreme.
- Seksioni "📋 PRECEDENTË TË CITUAR NË DOKUMENT" përmban precedentët 
  që dokumenti VETË i citon.

DETYRA:
A. PRECEDENTËT E CITUAR NË DOKUMENT (nëse ka)
   - Listoji ata që dokumenti i referon drejtpërdrejt
   - Vlerëso: a janë të saktë?

B. PRECEDENTËT E REKOMANDUAR (nga baza)
   - Listo 3-7 precedentë nga digest-i
   - Për secilin: numri + konteksti + pse është relevant

C. REKOMANDIMI
   - Nëse dokumenti NUK citon precedentë → rekomando shtimin
   - Nëse citon → vlerëso cilësinë

⚠️ NUK LEJOHET të shpikësh numra precedentësh. Përdor VETËM ata në digest.""",
    },

    "drafting_quality": {
        "title": "ANALIZA E CILËSISË SË HARTIMIT",
        "max_tokens": 2200,
        "prompt": """Ti je "Revizor i Cilësisë së Akteve Gjyqësore" në Kosovë.

Bazuar në digest-in, analizo CILËSINË E HARTIMIT.

DETYRA:
A. STRUKTURA FORMALE
B. TERMINOLOGJIA LIGJORE
C. ARSYETIMI JURIDIK
D. KONSISTENCA
E. VLERËSIMI I PËRGJITHSHËM

FORMATI:
## A. Struktura
## B. Terminologjia
## C. Arsyetimi
## D. Konsistenca
## E. Vlerësimi

NUK LEJOHET të shpikësh mangësi që nuk ekzistojnë.""",
    },

    "errors_corrections": {
        "title": "GABIME DHE KORRIGJIME",
        "max_tokens": 2600,
        "prompt": """Ti je "Revizor i Akteve Gjyqësore" në Kosovë.

Bazuar në digest-in, identifiko GABIME dhe propozo KORRIGJIME.

⚠️ RREGULLA ABSOLUTE:

1. GABIME NË NENE — Kontrollo VETËM nenet që shfaqen në digest.
   - NËSE digest-i thotë "Neni X ❌ NUK U GJET" → raportoje si gabim
   - NUK LEJOHET të krijosh gabime për nene që nuk ekzistojnë në dokument
   
2. GABIME FAKTIKE — Vetëm ato që janë të dukshme në digest.
   - Data që nuk përputhen brenda dokumentit
   - Numra lënde të ndryshëm
   
3. RREGULL I VEÇANTË:
   - Për çdo gabim, trego SE KU (faqe/paragraf) dhe CILA është e saktë
   - PËR ÇDO GABIM: "❌ [gabimi] → korrigjo me [e saktë] (impakti: X)"

FORMATI:
### A. Gabime në nene
### B. Gabime faktike
### C. Gabime procedurale
### D. Korrigjime të rekomanduara

NËSE NUK KA GABIME → shkruaj "Nuk u identifikuan gabime në këtë kategori."
NUK LEJOHET të shpikësh gabime.""",
    },

    "action_steps": {
        "title": "HAPAT KONKRET TË VEPRIMIT",
        "max_tokens": 2400,
        "prompt": """Ti je "Strateg i Lartë Ligjor" në Kosovë.

Bazuar në digest-in, harto PLANIN E VEPRIMIT.

DETYRA:
A. VLERËSIMI I SITUATËS
B. HAPAT E MENJËHERSHËM (1-7 ditë)
C. HAPAT AFATGJATË (1-3 muaj)
D. MUNDËSITË PROCEDURALE
E. RREZIQET

⚠️ RREGULLA KRITIKE PËR AFATET:
- Lexo me kujdes çdo afat që shfaqet në dokument (p.sh. "8 ditë ankim")
- NËSE dokumenti përmend afat specifik → CITOJE SAKTËSISHT
- NËSE dokumenti NUK përmend afat → shkruaj "Afati: kontrollo manualisht"
- NUK LEJOHET të shpikësh afate që nuk janë në dokument

FORMATI:
## A. Vlerësimi
## B. Hapat e menjëhershëm
## C. Hapat afatgjatë
## D. Mundësitë procedurale
## E. Rreziqet""",
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
            model=FAST_SEARCH_MODEL,
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
    V2.0 — Verifikim i një dokumenti me 4 guardrails anti-halucinacion.
    """

    def __init__(self, db):
        self.db = db

    # ────────────────────────────────────────────────────────────────────
    # GUARDRAIL #4 — Citation Checker (fjalë-për-fjalë)
    # ────────────────────────────────────────────────────────────────────

    def _verify_citations_word_by_word(
        self, output_text: str, doc_text: str
    ) -> Dict[str, Any]:
        """
        GUARDRAIL #4: Kontrollon çdo nen të output-it kundrejt dokumentit.
        Kthen raport me citimet e verifikuara / të pavërtetuara.
        """
        if not output_text or not doc_text:
            return {
                "verified": [],
                "unverified": [],
                "total_articles_output": 0,
                "total_articles_doc": 0,
                "hallucination_rate": 0.0,
            }

        # Nxjerr nenet nga dokumenti (burimi i së vërtetës)
        doc_articles: Set[str] = set()
        for match in VERIFIED_ARTICLE_PATTERN.finditer(doc_text):
            doc_articles.add(match.group(1))

        # Nxjerr nenet nga output-i
        verified: List[str] = []
        unverified: List[str] = []
        seen: Set[str] = set()

        for match in VERIFIED_ARTICLE_PATTERN.finditer(output_text):
            num = match.group(1)
            if num in seen:
                continue
            seen.add(num)

            if num in doc_articles:
                verified.append(num)
            else:
                unverified.append(num)

        total = len(seen)
        hallucination_rate = (
            round(len(unverified) / max(1, total) * 100, 1) if total > 0 else 0.0
        )

        return {
            "verified": sorted(verified),
            "unverified": sorted(unverified),
            "total_articles_output": total,
            "total_articles_doc": len(doc_articles),
            "doc_articles_available": sorted(doc_articles),
            "hallucination_rate": hallucination_rate,
        }

    # ────────────────────────────────────────────────────────────────────
    # GUARDRAIL #3 — Verifikim i Dyfishtë (LLM correction)
    # ────────────────────────────────────────────────────────────────────

    def _correct_citations_with_llm(
        self,
        output_text: str,
        checker_report: Dict[str, Any],
        doc_text: str,
    ) -> str:
        """
        GUARDRAIL #3: LLM i dytë pastron citimet halucinuese.
        Përdoret vetëm nëse Guardrail #4 ka gjetur nene të pavërtetuara.
        """
        unverified = checker_report.get("unverified", [])
        if not unverified:
            return output_text

        system_prompt = """Ti je "Verifikues i Saktësisë Ligjore" në Gjykatën Supreme të Kosovës.

DETYRA: Pastron output-in duke fshirë citimet e neneve që NUK ekzistojnë 
në DOKUMENTIN ORIGJINAL.

RREGULLA ABSOLUTE:
1. Për çdo nen që shfaqet në "NENET E PAVËRTETUARA" → FSHIJE ose KORRIGJOJE.
2. Ruaj çdo nen që EKZISTON vërtetë në dokument.
3. NUK LEJOHET të shtosh nene të re.
4. Ruaj strukturën, titujt, formatimin markdown.
5. NUK shpjego — kthe VETËM tekstin e pastruar."""

        user_content = f"""DOKUMENTI ORIGJINAL (burimi i së vërtetës):
{doc_text[:15000]}

───────────────────────────────────────────────────────

NENET QË NUK EKZISTOJNË NË DOKUMENT (duhen fshirë/korrigjuar):
{chr(10).join('❌ Neni ' + n for n in unverified)}

───────────────────────────────────────────────────────

OUTPUT-I QË DUHET PASTRUAR:
{output_text}

───────────────────────────────────────────────────────

Kthe tekstin e pastruar (pa nene të pavërtetuara):"""

        try:
            corrected = _call_llm(
                system_prompt=system_prompt,
                user_content=user_content,
                json_mode=False,
                temperature=0.0,
                model=FAST_SEARCH_MODEL,
            )
            return corrected or output_text
        except Exception as e:
            logger.warning(f"⚠️ [DOC_REVIEW] LLM correction failed: {e}")
            return output_text

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

        document = self._load_document(case_id, document_id)
        extraction = self._load_extraction(case_id, document_id)

        if not document and not extraction:
            return self._empty_result(case_id, document_id, "Document not found.")

        doc_text = (
            (extraction or {}).get("text")
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

        # ═══ GUARDRAIL #2: Regex ekstraktim para LLM ═══
        verified_citations = _extract_verified_citations(doc_text)
        logger.info(
            f"🔒 [GUARDRAIL #2] Regex extraction: "
            f"laws={verified_citations['total_laws']}, "
            f"articles={verified_citations['total_articles']}"
        )

        # Nxirr nenet e cituara (për KB verification)
        article_citations = self._extract_article_citations(doc_text)
        logger.info(
            f"📖 [DOC_REVIEW] Found {len(article_citations)} article citations"
        )

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

        cited_precedents = self._extract_cited_precedents(doc_text)
        logger.info(
            f"🏛️ [DOC_REVIEW] Found {len(cited_precedents)} cited precedents"
        )

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

        # Ndërto digest me citimet e vërtetuara
        digest = self._build_review_digest(
            document=document,
            extraction=extraction,
            document_type=document_type,
            file_name=file_name,
            article_citations=article_citations,
            article_verifications=article_verifications,
            cited_precedents=cited_precedents,
            recommended_precedents=recommended_precedents,
            verified_citations=verified_citations,
            doc_text=doc_text,
        )

        logger.info(
            f"🔍 [DOC_REVIEW] Digest built: {len(digest)} chars, "
            f"articles_verified={len(article_verifications)}, "
            f"precedents_recommended={len(recommended_precedents)}"
        )

        # Gjenero 6 seksionet
        sections: Dict[str, Any] = {}
        section_stats: Dict[str, Any] = {}
        verification_reports: Dict[str, Any] = {}

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

                # ═══ GUARDRAILS #3 + #4 për article_verification ═══
                if section_key == "article_verification" and content:
                    logger.info("🔍 [GUARDRAIL #4] Running citation checker...")
                    checker_report = self._verify_citations_word_by_word(
                        content, doc_text
                    )
                    verification_reports[section_key] = checker_report

                    logger.info(
                        f"📊 [GUARDRAIL #4] Verified: {len(checker_report['verified'])}, "
                        f"Unverified: {len(checker_report['unverified'])}, "
                        f"Hallucination rate: {checker_report['hallucination_rate']}%"
                    )

                    # Nëse ka halucinacione → korrigjo me LLM #2
                    if checker_report["unverified"]:
                        logger.info(
                            f"🔧 [GUARDRAIL #3] Correcting "
                            f"{len(checker_report['unverified'])} unverified citations..."
                        )
                        corrected_content = self._correct_citations_with_llm(
                            content, checker_report, doc_text
                        )

                        # Re-verify pas korrigjimit
                        report_after = self._verify_citations_word_by_word(
                            corrected_content, doc_text
                        )
                        logger.info(
                            f"✅ [GUARDRAIL #3] After correction: "
                            f"hallucination_rate={report_after['hallucination_rate']}%"
                        )

                        content = corrected_content
                        verification_reports[section_key] = {
                            **checker_report,
                            "after_correction": report_after,
                        }

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
                "verified_laws_count": verified_citations["total_laws"],
                "verified_articles_count": verified_citations["total_articles"],
            },
            "verification_details": {
                "article_verifications": article_verifications,
                "cited_precedents": cited_precedents,
                "recommended_precedents": recommended_precedents,
                "regex_verified_citations": verified_citations,
                "guardrail_reports": verification_reports,
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
    # ARTICLE EXTRACTION (existing)
    # ────────────────────────────────────────────────────────────────────

    def _extract_article_citations(self, text: str) -> List[Dict[str, Any]]:
        if not text:
            return []

        citations: List[Dict[str, Any]] = []
        seen: Set[Tuple[str, str]] = set()

        for match in ARTICLE_PATTERN.finditer(text):
            article_number = match.group(1).strip()
            law_hint = (match.group(2) or "").strip()

            if law_hint:
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
    # ARTICLE VERIFICATION (existing)
    # ────────────────────────────────────────────────────────────────────

    def _verify_articles_against_kb(
        self, citations: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        verifications: Dict[str, Dict[str, Any]] = {}
        citations_to_check = citations[:MAX_KB_LOOKUPS]

        for i, citation in enumerate(citations_to_check):
            article_num = citation["article_number"]
            law_hint = citation["law_hint"]

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

            statute_matches = []
            precedent_matches = []

            for r in kb_results:
                src = (r.get("source") or "").lower()
                txt = (r.get("text") or "").lower()

                is_statute = (
                    "baza statutore" in src
                    or "neni" in src
                )
                is_precedent = (
                    "precedent" in src
                    or "gjykatës supreme" in src
                    or "gjykatës sup" in src
                )

                article_pattern = re.compile(
                    rf'\bneni\s+{re.escape(article_num)}\b',
                    re.IGNORECASE,
                )

                if is_statute and article_pattern.search(txt):
                    statute_matches.append(r)
                elif is_precedent:
                    if article_pattern.search(txt):
                        precedent_matches.append(r)
                    elif law_hint and law_hint.lower() in txt:
                        precedent_matches.append(r)

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
    # PRECEDENT EXTRACTION (existing)
    # ────────────────────────────────────────────────────────────────────

    def _extract_cited_precedents(self, text: str) -> List[str]:
        if not text:
            return []

        matches = CASE_NUMBER_PATTERN.findall(text)
        seen = set()
        result = []
        for m in matches:
            m_clean = re.sub(r'\s+', ' ', m.strip())
            if m_clean.lower() not in seen:
                seen.add(m_clean.lower())
                result.append(m_clean)

        return result

    # ────────────────────────────────────────────────────────────────────
    # RECOMMENDED PRECEDENTS (existing)
    # ────────────────────────────────────────────────────────────────────

    def _find_recommended_precedents(
        self,
        doc_text: str,
        citations: List[Dict[str, Any]],
        cited_precedents: List[str],
    ) -> List[Dict[str, Any]]:
        recommended: Dict[str, Dict[str, Any]] = {}
        cited_lower = {c.lower() for c in cited_precedents}

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
                if case_lower in cited_lower:
                    continue
                if case_lower in recommended:
                    continue

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

        sorted_recommended = sorted(
            recommended.values(),
            key=lambda x: x["similarity"],
            reverse=True,
        )

        return sorted_recommended[:10]

    def _compute_similarity(self, text_a: str, text_b: str) -> float:
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
        verified_citations: Dict[str, Any],
        doc_text: str,
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
        lines.append(f"Madhësia: {len(doc_text)} chars")
        lines.append("")

        # ═══ 2. GUARDRAIL #2: CITIMET E VËRTETUARA (REGEX) ═══
        lines.append("=" * 70)
        lines.append("🔒 CITIMET E VËRTETUARA NGA DOKUMENTI (REGEX EXTRACTION)")
        lines.append("=" * 70)
        lines.append(
            "⚠️ KY ËSHTË BURIMI I VETËM I SË VËRTETËS. "
            "LLM NUK LEJOHET TË SHPIKË LIGJE APO NENE QË NUK SHFAQEN KËTU."
        )
        lines.append("")

        lines.append(f"LIGJET E CITUARA ({verified_citations['total_laws']}):")
        if verified_citations["laws"]:
            for law in verified_citations["laws"]:
                lines.append(f"  • {law}")
        else:
            lines.append("  (asnjë ligj i cituar në dokument)")
        lines.append("")

        lines.append(f"NENET E CITUARA ({verified_citations['total_articles']}):")
        if verified_citations["articles"]:
            for art in verified_citations["articles"]:
                par = f", par. {art['paragraph']}" if art["paragraph"] else ""
                lines.append(f"  • Neni {art['number']}{par}")
        else:
            lines.append("  (asnjë nen i cituar në dokument)")
        lines.append("")

        lines.append(
            "⚠️ RREGULL ABSOLUT: Përdor VETËM ligjet dhe nenet e mësipërme. "
            "ÇDO ligj/nen që nuk është në këtë listë KONSIDEROHET "
            "HALUDINACION dhe do të fshihet automatikisht."
        )
        lines.append("")

        # ═══ 3. FILLIMI I DOKUMENTIT ═══
        if doc_text:
            excerpt = doc_text[:3000]
            lines.append("=" * 70)
            lines.append("FILLIMI I DOKUMENTIT (për kontekst)")
            lines.append("=" * 70)
            lines.append(excerpt)
            lines.append("")

        # ═══ 4. VERIFIKIMI I NENEVE (KB) ═══
        if article_verifications:
            lines.append("=" * 70)
            lines.append("📖 VERIFIKIMI I NENEVE (kundrejt bazës ligjore)")
            lines.append("=" * 70)
            lines.append(
                f"Gjithsej {len(article_verifications)} nene të verifikuara."
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
            lines.append("NUK U IDENTIFIKUAN nene të cituara në këtë dokument.")
            lines.append("")

        # ═══ 5. PRECEDENTË TË CITUAR ═══
        lines.append("=" * 70)
        lines.append("📋 PRECEDENTË TË CITUAR NË DOKUMENT")
        lines.append("=" * 70)
        if cited_precedents:
            for cn in cited_precedents:
                lines.append(f"  • {cn}")
        else:
            lines.append("  (asnjë precedent i cituar në dokument)")
        lines.append("")

        # ═══ 6. PRECEDENTË TË REKOMANDUAR ═══
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

        # ═══ 7. METAINFO ═══
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
                        model=FAST_SEARCH_MODEL,
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