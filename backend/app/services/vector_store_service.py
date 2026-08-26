# FILE: backend/app/services/vector_store_service.py
# PHOENIX PROTOCOL - SAAS VECTOR STORE V30.0 (DUAL-STRATA SUPREME COURT & STATUTORY RETRIEVAL)

import os, time, logging, json
from typing import List, Dict, Any, Sequence
from pymongo import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)


def _sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    return {k: (v if isinstance(v, (str, int, float, bool)) else json.dumps(v, ensure_ascii=False)) for k, v in metadata.items()}


def _get_db():
    uri = os.getenv("DATABASE_URI")
    db_name = os.getenv("MONGO_DB_NAME", "advocatus_db")
    return MongoClient(uri)[db_name]


def get_global_collection(): 
    return None 


def query_global_knowledge_base(query_text: str, n_results: int = 14, **kwargs) -> List[Dict[str, Any]]:
    """
    DUAL-STRATA RETRIEVAL ENGINE:
    Retrieves both Statutory Articles (Gazeta Zyrtare) and Supreme Court Precedents (Aktgjykimet e Supremes).
    """
    from . import embedding_service
    vector = embedding_service.generate_embedding(query_text) if query_text else None
    
    db = _get_db()
    coll = db["legal_knowledge_base"]
    raw_results = []

    if vector:
        try:
            pipeline = [{
                "$vectorSearch": {
                    "index": "vector_index", 
                    "path": "embedding", 
                    "queryVector": vector, 
                    "numCandidates": 120, 
                    "limit": n_results
                }
            }]
            raw_results = list(coll.aggregate(pipeline))
        except Exception as e:
            logger.warning(f"SaaS Global Vector Query Failed, running text fallback: {e}")

    # Fallback to Text Search if vector search returns empty
    if not raw_results:
        try:
            raw_results = list(coll.find({"$text": {"$search": query_text}}).limit(n_results))
        except Exception:
            raw_results = list(coll.find().limit(n_results))

    formatted_results = []
    for r in raw_results:
        law_title = r.get("law_title") or r.get("title") or "Dokument Juridik"
        article_num = str(r.get("article_number", ""))
        is_article = r.get("is_article", False)
        is_case_law = r.get("is_case_law", False) or "pml" in law_title.lower() or "supreme" in law_title.lower()

        # Contextual tagging for LLM synthesis
        if is_case_law:
            source_tag = f"🔨 Praktika Gjyqësore & Vendim Parimor i Gjykatës Supreme: {law_title}"
        elif is_article:
            art_label = "Neni " if article_num != "0" else "Preambula"
            art_suffix = article_num if article_num != "0" else ""
            source_tag = f"⚖️ Baza Statutare: {law_title}, {art_label}{art_suffix}"
        else:
            section_label = article_num if article_num else "Seksioni"
            source_tag = f"📚 Doktrina dhe Komentari Zyrtar ({law_title}), {section_label}"

        formatted_results.append({
            "text": r.get("text") or r.get("content") or "", 
            "source": source_tag, 
            "chunk_id": str(r.get("_id", ""))
        })

    return formatted_results


def query_case_knowledge_base(user_id: str, query_text: str, n_results: int = 16, **kwargs) -> List[Dict[str, Any]]:
    """
    UNBREAKABLE DUAL-RETRIEVAL ENGINE:
    1. Executes Atlas $vectorSearch with case_id + owner_id filter.
    2. Fallback: Directly queries db.user_vectors & db.documents for full extracted text.
    """
    from . import embedding_service
    case_context_id = kwargs.get("case_context_id") or kwargs.get("case_id")
    vector = embedding_service.generate_embedding(query_text) if query_text else None
    
    db = _get_db()
    coll = db["user_vectors"]
    results = []

    case_filter: Dict[str, Any] = {"owner_id": user_id}
    if case_context_id:
        case_id_str = str(case_context_id)
        case_filter["$or"] = [
            {"case_id": case_id_str},
            {"case_id": ObjectId(case_id_str) if ObjectId.is_valid(case_id_str) else case_id_str}
        ]

    # Step 1: Vector Search
    if vector:
        try:
            pipeline = [{
                "$vectorSearch": {
                    "index": "vector_index", 
                    "path": "embedding", 
                    "queryVector": vector, 
                    "numCandidates": 120, 
                    "limit": n_results, 
                    "filter": {"owner_id": user_id}
                }
            }]
            results = list(coll.aggregate(pipeline))
        except Exception as e:
            logger.warning(f"Vector search exception: {e}")

    # Step 2: Direct Fallback
    if not results:
        try:
            results = list(coll.find(case_filter).limit(n_results))
        except Exception as e:
            logger.error(f"Direct user_vectors fetch failed: {e}")

        if not results and case_context_id:
            try:
                c_oid = ObjectId(case_context_id) if ObjectId.is_valid(case_context_id) else case_context_id
                doc_cursor = db.documents.find({"$or": [{"case_id": case_context_id}, {"case_id": c_oid}], "status": {"$ne": "DELETED"}})
                docs = list(doc_cursor)
                
                fallback_chunks = []
                for doc in docs:
                    text_content = doc.get("extracted_text") or doc.get("summary") or ""
                    if text_content and text_content != "Sinteza...":
                        file_name = doc.get("file_name") or doc.get("title") or "Dokument i Lëndës"
                        fallback_chunks.append({
                            "text": text_content[:3000],
                            "source": file_name,
                            "page": 1
                        })
                return fallback_chunks
            except Exception as doc_err:
                logger.error(f"Direct document fallback failed: {doc_err}")

    return [{"text": r.get("text", ""), "source": r.get("file_name", "Doc"), "page": r.get("page", "1")} for r in results]


def create_and_store_embeddings_from_chunks(
    user_id: str, 
    document_id: str, 
    case_id: str, 
    file_name: str, 
    chunks: List[str], 
    metadatas: Sequence[Dict[str, Any]]
) -> bool:
    from . import embedding_service
    
    if not chunks:
        logger.warning(f"⚠️ [VectorStore] 0 chunks provided for document {document_id}")
        return False

    try:
        vectors = embedding_service.generate_embeddings_batch(chunks)
        
        coll = _get_db()["user_vectors"]
        docs = []
        for i, chunk in enumerate(chunks):
            vector = vectors[i] if i < len(vectors) else []
            meta = metadatas[i] if i < len(metadatas) else {}
            docs.append({
                "owner_id": user_id, 
                "document_id": document_id, 
                "case_id": case_id, 
                "file_name": file_name,
                "text": chunk, 
                "embedding": vector if vector else [], 
                **meta
            })
        
        if docs: 
            coll.insert_many(docs)
            logger.info(f"✅ SaaS Ingested {len(docs)} chunks for document {document_id}!")
            return True
        return False
            
    except Exception as e:
        logger.error(f"SaaS Ingestion Failed: {e}")
        return False


def delete_document_embeddings(user_id: str, document_id: str):
    try: 
        _get_db()["user_vectors"].delete_many({"document_id": document_id, "owner_id": user_id})
    except Exception: 
        pass


def copy_document_embeddings(source_document_id: str, target_document_id: str, target_user_id: str, target_case_id: str):
    try:
        db = _get_db()
        existing = list(db["user_vectors"].find({"document_id": source_document_id}))
        for doc in existing:
            doc.pop("_id", None)
            doc.update({"document_id": target_document_id, "owner_id": target_user_id, "case_id": target_case_id})
        if existing: 
            db["user_vectors"].insert_many(existing)
    except Exception: 
        pass