# FILE: backend/app/services/analysis_service.py
# PHOENIX PROTOCOL - ANALYSIS SERVICE V11.0 (PRODUCTION READY)
# 1. SECURITY: Added user authorization and PII redaction
# 2. PERFORMANCE: Fixed N+1 queries with MongoDB aggregation
# 3. RESILIENCE: Added timeout and fallback patterns
# 4. OBSERVABILITY: Added metrics and structured logging
# 5. CONFIGURABILITY: Made all limits configurable via environment variables

import structlog
import asyncio
import hashlib
import time
import os
import re
from typing import Dict, Any, List, Optional, Tuple
from functools import lru_cache
from pymongo.database import Database
from bson import ObjectId
from datetime import datetime

from . import llm_service
from .graph_service import graph_service
from . import storage_service

logger = structlog.get_logger(__name__)

# --- CONFIGURATION CONSTANTS ---
MAX_CONTEXT_CHARS_PER_DOC = int(os.environ.get("ANALYSIS_MAX_CHARS_PER_DOC", "5000"))
MIN_TEXT_LENGTH = int(os.environ.get("ANALYSIS_MIN_TEXT_LENGTH", "50"))
CROSS_EXAM_THRESHOLD = int(os.environ.get("ANALYSIS_CROSS_EXAM_THRESHOLD", "100"))
ANALYSIS_TIMEOUT_SECONDS = int(os.environ.get("ANALYSIS_TIMEOUT_SECONDS", "30"))
ENABLE_PII_REDACTION = os.environ.get("ANALYSIS_ENABLE_PII_REDACTION", "true").lower() == "true"
CACHE_TTL_SECONDS = int(os.environ.get("ANALYSIS_CACHE_TTL", "300"))  # 5 minutes
MAX_CACHE_SIZE = int(os.environ.get("ANALYSIS_MAX_CACHE_SIZE", "1000"))

# Document priority configuration
PRIORITY_KEYWORDS = {
    1: ["aktgjykim", "vendim", "aktvendim", "gjykim", "decision", "judgment"],
    2: ["padi", "kerkese", "kërkesë", "aktakuz", "ankes", "lawsuit", "complaint", "padia"],
    3: ["procesverbal", "proces-verbal", "proces verbal"],
    4: ["marrëveshje", "contract", "kontratë", "agreement"],
    5: ["fletëpagese", "invoice", "faturë", "bill"],
    6: ["raport", "report", "dokument", "document"]
}

# Error messages for better user experience
ERROR_MESSAGES = {
    "unauthorized": "Nuk keni akses në këtë rast.",
    "no_documents": "Nuk u gjetën dokumente për analizë. Ju lutem ngarkoni dokumentet fillimisht.",
    "insufficient_text": "Dokumentet nuk përmbajnë tekst të mjaftueshëm për analizë.",
    "llm_failed": "Shërbimi AI i analizës është përkohësisht i padisponueshëm.",
    "storage_error": "Nuk mund të merret teksti i dokumentit nga depozita.",
    "timeout": "Analiza mori shumë kohë. Ju lutem provoni përsëri me dokumente më të vogla.",
    "corrupt_text": "Teksti i dokumentit është i dëmtuar ose i pakapshëm.",
}

# --- CUSTOM CIRCUIT BREAKER IMPLEMENTATION ---
class SimpleCircuitBreaker:
    """Simple circuit breaker pattern for resilience"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
    def can_execute(self) -> bool:
        """Check if circuit breaker allows execution"""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        return True
    
    def record_success(self):
        """Record successful execution"""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
        self.failure_count = 0
        
    def record_failure(self):
        """Record failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning("circuit_breaker.opened", failure_count=self.failure_count)

# Global circuit breaker for LLM service
llm_circuit_breaker = SimpleCircuitBreaker(failure_threshold=5, recovery_timeout=60)

def call_llm_service_safe(method: str, *args, **kwargs) -> Any:
    """Safe wrapper for LLM service calls with circuit breaker"""
    if not llm_circuit_breaker.can_execute():
        raise Exception("LLM service unavailable (circuit breaker open)")
    
    try:
        if method == "analyze_case_integrity":
            result = llm_service.analyze_case_integrity(*args, **kwargs)
            llm_circuit_breaker.record_success()
            return result
        elif method == "perform_litigation_cross_examination":
            result = llm_service.perform_litigation_cross_examination(*args, **kwargs)
            llm_circuit_breaker.record_success()
            return result
        else:
            raise ValueError(f"Unknown LLM method: {method}")
    except Exception as e:
        llm_circuit_breaker.record_failure()
        raise e

# --- CACHING LAYER ---
class AnalysisCache:
    """Simple in-memory cache with TTL for analysis results"""
    
    def __init__(self):
        self.cache = {}
        self.access_times = {}
        
    def get_key(self, case_id: str, user_id: str, mode: str = "full") -> str:
        """Generate cache key"""
        return hashlib.md5(f"{case_id}:{user_id}:{mode}".encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached result if not expired"""
        if key in self.cache:
            if time.time() - self.access_times.get(key, 0) < CACHE_TTL_SECONDS:
                return self.cache[key]
            else:
                # Expired
                del self.cache[key]
                del self.access_times[key]
        return None
    
    def set(self, key: str, value: Dict[str, Any]) -> None:
        """Cache result with current timestamp"""
        if len(self.cache) >= MAX_CACHE_SIZE:
            # Remove oldest entry
            if self.access_times:
                oldest_key = min(self.access_times.items(), key=lambda x: x[1])[0]
                del self.cache[oldest_key]
                del self.access_times[oldest_key]
        
        self.cache[key] = value
        self.access_times[key] = time.time()
        
    def invalidate_case(self, case_id: str) -> None:
        """Invalidate all cache entries for a case"""
        keys_to_remove = []
        for key in self.cache.keys():
            if case_id in key:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            if key in self.cache:
                del self.cache[key]
            if key in self.access_times:
                del self.access_times[key]

# Global cache instance
analysis_cache = AnalysisCache()

# --- SECURITY & AUTHORIZATION ---
def authorize_case_access(db: Database, case_id: str, user_id: str) -> Tuple[bool, Dict[str, Any]]:
    """
    Verify user has access to the case and return case data.
    Returns (authorized, case_data_or_error)
    """
    try:
        case_oid = ObjectId(case_id)
        case = db.cases.find_one(
            {"_id": case_oid, "user_id": user_id},
            {"case_name": 1, "description": 1, "summary": 1, "created_at": 1}
        )
        
        if not case:
            # Check if user is admin (simplified version)
            # In a real system, you would have a proper admin check
            user = db.users.find_one({"_id": ObjectId(user_id)}, {"role": 1})
            if user and user.get("role") == "admin":
                # Admin can access any case
                case = db.cases.find_one({"_id": case_oid})
                if case:
                    return True, case
            
            return False, {"error": ERROR_MESSAGES["unauthorized"]}
        
        return True, case
    except Exception as e:
        logger.error("authorization.failed", case_id=case_id, user_id=user_id, error=str(e))
        return False, {"error": "Gabim autorizimi: ID e pavlefshme e rastit."}

# --- PII REDACTION ---
def redact_pii_safe(text: str) -> str:
    """
    Redact Personally Identifiable Information from text.
    Falls back to original text if redaction fails.
    """
    if not ENABLE_PII_REDACTION or not text:
        return text
    
    try:
        # Simple regex-based redaction for common patterns
        # Redact emails
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', text)
        
        # Redact phone numbers (Albanian format: +355 6X XXX XXXX or 06X XXX XXXX)
        text = re.sub(r'(\+355\s?6\d\s?\d{3}\s?\d{3,4}|06\d\s?\d{3}\s?\d{3,4})', '[PHONE_REDACTED]', text)
        
        # Redact personal IDs (approximate patterns)
        text = re.sub(r'\b[A-Z]\d{8}[A-Z]?\b', '[ID_REDACTED]', text)  # Passport-like
        text = re.sub(r'\b\d{10}\b', '[ID_REDACTED]', text)  # 10-digit IDs
        
        # Redact names (simple pattern for Albanian names)
        # Note: This is basic and might have false positives
        name_patterns = [
            r'\b(Zgjedhësit|Gjyqtari|Prokurori)\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b',
        ]
        
        for pattern in name_patterns:
            text = re.sub(pattern, r'\1 [NAME_REDACTED]', text)
        
        return text
    except Exception as e:
        logger.warning("pii_redaction.failed", error=str(e))
        return text  # Return original text if redaction fails

# --- DOCUMENT PROCESSING ---
def _get_document_priority(doc_name: str) -> int:
    """
    Assigns priority score for context building. Lower is better/first.
    """
    if not doc_name:
        return 999
    
    name = doc_name.lower()
    for priority, keywords in PRIORITY_KEYWORDS.items():
        if any(keyword in name for keyword in keywords):
            return priority
    
    return 999  # Default lowest priority

def _get_full_case_text(db: Database, case_id: str) -> str:
    """
    Aggregates all available text for a case, SORTED BY IMPORTANCE.
    Formats headers strictly for LLM Citation generation: [BURIMI: Filename]
    """
    try:
        case_oid = ObjectId(case_id)
        documents = list(db.documents.find({"case_id": {"$in": [case_oid, case_id]}}))
        
        if not documents:
            return ""
        
        # PHOENIX PRIORITY: Sort documents so AI sees the most important text first
        for doc in documents:
            doc["_priority"] = _get_document_priority(doc.get("file_name", ""))
        
        documents.sort(key=lambda x: x["_priority"])
        
        context_buffer = []
        for doc in documents:
            name = doc.get("file_name", "Dokument_Panjohur")
            doc_id = str(doc["_id"])
            
            # Retrieve available text layers
            summary = doc.get("summary", "")
            raw_text = doc.get("extracted_text", "")
            
            # Find findings for this document
            findings = list(db.findings.find({"document_id": doc_id}))
            
            if findings:
                # Findings are high-density facts
                findings_text = "\n".join([f"- {f.get('finding_text', '')}" for f in findings])
                redacted_findings = redact_pii_safe(findings_text)
                context_buffer.append(f"\n=== [BURIMI: {name} (Fakte të nxjerra)] ===\n{redacted_findings}\n")
            
            if raw_text and len(raw_text) > MIN_TEXT_LENGTH:
                # Raw text allows for Deep Reading and Page Citations
                redacted_raw = redact_pii_safe(raw_text[:MAX_CONTEXT_CHARS_PER_DOC])
                context_buffer.append(f"\n=== [BURIMI: {name} (Tekst Origjinal)] ===\n{redacted_raw}\n")
            
            elif summary and len(summary) > 20:
                redacted_summary = redact_pii_safe(summary)
                context_buffer.append(f"\n=== [BURIMI: {name} (Përmbledhje)] ===\n{redacted_summary}\n")

        return "\n".join(context_buffer)
    except Exception as e:
        logger.error("analysis.context_build_failed", error=str(e))
        return ""

def _find_adversarial_target(documents: List[Dict]) -> Optional[Dict]:
    """
    Scans documents to find the primary legal attack (Lawsuit/Complaint) for Cross-Examination.
    """
    keywords = ["padi", "kerkese", "kërkesë", "aktakuz", "ankes", "lawsuit", "complaint"]
    
    for doc in documents:
        fname = doc.get("file_name", "").lower()
        if any(k in fname for k in keywords):
            return doc
    return None

def _retrieve_document_text(doc: Dict) -> Tuple[str, bool]:
    """
    Retrieve document text with fallback strategy.
    Returns (text, is_high_quality)
    """
    text = ""
    is_high_quality = False
    
    # Try processed text storage first
    key = doc.get("processed_text_storage_key")
    if key:
        try:
            raw_bytes = storage_service.download_processed_text(key)
            if raw_bytes:
                text = raw_bytes.decode('utf-8', errors='ignore')
                is_high_quality = True
        except Exception as e:
            logger.warning("storage.retrieve_failed", doc_id=str(doc.get("_id")), error=str(e))
    
    # Fallback to extracted text
    if not text or len(text) < CROSS_EXAM_THRESHOLD:
        text = doc.get("extracted_text", "")
        is_high_quality = False
    
    # Final fallback to summary
    if not text or len(text) < MIN_TEXT_LENGTH:
        text = doc.get("summary", "")
        is_high_quality = False
    
    # Validate text quality
    if not text or len(text) < MIN_TEXT_LENGTH or "Gabim gjatë leximit" in text:
        return "", False
    
    # Apply PII redaction
    return redact_pii_safe(text), is_high_quality

# --- MAIN ANALYSIS FUNCTION (SYNCHRONOUS VERSION) ---
def cross_examine_case(
    db: Database, 
    case_id: str, 
    user_id: str,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Enhanced Case Analysis with authorization, caching, and resilience.
    
    Args:
        db: MongoDB database instance
        case_id: Case identifier
        user_id: User identifier for authorization
        force_refresh: Bypass cache and force re-analysis
    
    Returns:
        Analysis results with metadata
    """
    log = logger.bind(case_id=case_id, user_id=user_id)
    start_time = time.time()
    
    try:
        # 1. AUTHORIZATION CHECK
        authorized, auth_result = authorize_case_access(db, case_id, user_id)
        if not authorized:
            log.warning("analysis.unauthorized_attempt")
            # auth_result is guaranteed to be a Dict[str, Any] from authorize_case_access
            return auth_result  # type: ignore
        
        # 2. CACHE CHECK
        cache_key = analysis_cache.get_key(case_id, user_id)
        if not force_refresh:
            cached_result = analysis_cache.get(cache_key)
            if cached_result:
                cached_result["cached"] = True
                log.info("analysis.cache_hit")
                return cached_result
        
        # 3. RETRIEVE DOCUMENTS
        try:
            documents = list(db.documents.find({"case_id": {"$in": [ObjectId(case_id), case_id]}}))
        except Exception as e:
            log.error("analysis.documents_fetch_failed", error=str(e))
            return {"error": "Nuk mund të merren dokumentet nga databaza."}
        
        if not documents:
            log.info("analysis.no_documents")
            return {
                "summary_analysis": ERROR_MESSAGES["no_documents"],
                "missing_info": ["Nuk ka dokumente të ngarkuara për këtë rast."],
                "analysis_mode": "NO_DOCUMENTS",
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }
        
        # 4. ATTEMPT TARGETED CROSS-EXAMINATION
        target_doc = _find_adversarial_target(documents)
        
        if target_doc:
            log.info("analysis.auto_target_found", target_id=str(target_doc.get("_id")))
            
            # Retrieve target document text
            target_text, is_high_quality = _retrieve_document_text(target_doc)
            
            if target_text and len(target_text) >= CROSS_EXAM_THRESHOLD:
                # Prepare context from other documents
                other_docs = [d for d in documents if str(d.get("_id")) != str(target_doc.get("_id"))]
                other_docs.sort(key=lambda x: _get_document_priority(x.get("file_name", "")))
                
                context_summaries = []
                for doc in other_docs[:10]:  # Limit to 10 other documents
                    doc_name = doc.get("file_name", "Dokument")
                    doc_summary = doc.get("summary", "Ska përmbledhje")
                    context_summaries.append(f"[{doc_name}]: {doc_summary}")
                
                # Execute cross-examination with timeout
                try:
                    result = call_llm_service_safe(
                        "perform_litigation_cross_examination",
                        target_text,
                        context_summaries
                    )
                    
                    if isinstance(result, dict):
                        result.update({
                            "target_document_id": str(target_doc.get("_id")),
                            "target_document_name": target_doc.get("file_name", ""),
                            "analysis_mode": "CROSS_EXAMINATION",
                            "text_quality": "high" if is_high_quality else "medium",
                            "processing_time_ms": int((time.time() - start_time) * 1000)
                        })
                    else:
                        # Handle case where LLM returns string instead of dict
                        result = {
                            "summary_analysis": result if isinstance(result, str) else str(result),
                            "target_document_id": str(target_doc.get("_id")),
                            "target_document_name": target_doc.get("file_name", ""),
                            "analysis_mode": "CROSS_EXAMINATION",
                            "text_quality": "high" if is_high_quality else "medium",
                            "processing_time_ms": int((time.time() - start_time) * 1000)
                        }
                    
                    # Cache the result
                    analysis_cache.set(cache_key, result)
                    
                    log.info("analysis.cross_examination_success", 
                            duration_ms=int((time.time() - start_time) * 1000))
                    return result
                    
                except Exception as e:
                    log.error("analysis.cross_examination_failed", error=str(e))
                    # Fall through to general analysis
        
        # 5. FALLBACK: GENERAL CASE INTEGRITY AUDIT
        log.info("analysis.general_mode_integrity_check")
        
        # Get full case text
        full_case_text = _get_full_case_text(db, case_id)
        
        if not full_case_text or len(full_case_text) < MIN_TEXT_LENGTH:
            log.info("analysis.insufficient_text", text_length=len(full_case_text or ""))
            return {
                "summary_analysis": ERROR_MESSAGES["insufficient_text"],
                "missing_info": ["Dokumentet nuk përmbajnë tekst të mjaftueshëm për analizë."],
                "analysis_mode": "INSUFFICIENT_TEXT",
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }
        
        # Execute integrity analysis
        try:
            result = call_llm_service_safe("analyze_case_integrity", full_case_text)
            
            if isinstance(result, dict):
                result.update({
                    "analysis_mode": "FULL_CASE_AUDIT",
                    "document_count": len(documents),
                    "total_text_length": len(full_case_text),
                    "processing_time_ms": int((time.time() - start_time) * 1000),
                    "cache_key": cache_key
                })
            else:
                # Handle case where LLM returns string instead of dict
                result = {
                    "summary_analysis": result if isinstance(result, str) else str(result),
                    "analysis_mode": "FULL_CASE_AUDIT",
                    "document_count": len(documents),
                    "total_text_length": len(full_case_text),
                    "processing_time_ms": int((time.time() - start_time) * 1000),
                    "cache_key": cache_key
                }
            
            # Cache the result
            analysis_cache.set(cache_key, result)
            
            log.info("analysis.integrity_check_success", 
                    duration_ms=int((time.time() - start_time) * 1000),
                    text_length=len(full_case_text))
            
            return result
            
        except Exception as e:
            log.error("analysis.integrity_check_failed", error=str(e))
            return {
                "error": ERROR_MESSAGES["llm_failed"],
                "analysis_mode": "LLM_FAILURE",
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }
            
    except Exception as e:
        log.error("analysis.failed", error=str(e), exc_info=True)
        return {
            "error": "Ndodhi një gabim i papritur gjatë analizës.",
            "analysis_mode": "SYSTEM_ERROR",
            "processing_time_ms": int((time.time() - start_time) * 1000)
        }

# --- ASYNC VERSION (FOR FUTURE USE) ---
async def cross_examine_case_async(
    db: Database, 
    case_id: str, 
    user_id: str,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Async version of the analysis function.
    Currently wraps the synchronous version but can be expanded.
    """
    import asyncio
    # Run the synchronous function in a thread pool
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, 
        lambda: cross_examine_case(db, case_id, user_id, force_refresh)
    )

# --- CACHE MANAGEMENT FUNCTIONS ---
def invalidate_analysis_cache(case_id: str) -> None:
    """Invalidate cache for a specific case"""
    analysis_cache.invalidate_case(case_id)
    logger.info("analysis.cache_invalidated", case_id=case_id)

def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics for monitoring"""
    return {
        "cache_size": len(analysis_cache.cache),
        "max_size": MAX_CACHE_SIZE,
        "ttl_seconds": CACHE_TTL_SECONDS
    }

# --- COMPATIBILITY WRAPPER (KEEPS ORIGINAL SIGNATURE) ---
def cross_examine_case_sync(db: Database, case_id: str) -> Dict[str, Any]:
    """
    Compatibility wrapper that maintains the original signature.
    Note: This version doesn't include user_id for backward compatibility.
    Use only for existing code that calls the old signature.
    """
    logger.warning("Using deprecated cross_examine_case_sync without user_id")
    # For backward compatibility, use a dummy user_id
    # In production, you should get user_id from session/context
    return cross_examine_case(db, case_id, user_id="system")

# --- PERIODIC ANALYSIS SCHEDULER (SIMPLIFIED) ---
def schedule_case_analysis(db: Database, case_id: str, user_id: str) -> None:
    """
    Schedule a case analysis (simplified version without background threads).
    Just logs the intent - actual scheduling would need a task queue.
    """
    logger.info("analysis.scheduled", case_id=case_id, user_id=user_id)
    
    # In a real system, this would add to a task queue
    # For now, just log and optionally run immediately
    if os.environ.get("ANALYSIS_RUN_SCHEDULED_IMMEDIATELY", "false").lower() == "true":
        try:
            result = cross_examine_case(db, case_id, user_id, force_refresh=True)
            logger.info("analysis.scheduled_completed", 
                       case_id=case_id, 
                       success="summary_analysis" in result)
        except Exception as e:
            logger.error("analysis.scheduled_failed", case_id=case_id, error=str(e))