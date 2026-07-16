# FILE: backend/app/services/vector_store_service.py
# PHOENIX PROTOCOL - VECTOR STORE V22.0 (TOTAL RECOVERY)
# STATUS: Multi-member API Restored / Cloud-AI Integrated

import os, time, logging, json
from typing import List, Dict, Optional, Any, Sequence
import chromadb
from chromadb.api.models.Collection import Collection

logger = logging.getLogger(__name__)

def _sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    return {k: (v if isinstance(v, (str, int, float, bool)) else json.dumps(v, ensure_ascii=False)) for k, v in metadata.items()}

def get_client():
    from ..main import app
    if not hasattr(app.state, "chroma_client") or app.state.chroma_client is None:
        persist_dir = os.path.join(os.getcwd(), "data", "chroma")
        os.makedirs(persist_dir, exist_ok=True)
        app.state.chroma_client = chromadb.PersistentClient(path=persist_dir)
    return app.state.chroma_client

def get_global_collection() -> Collection: return get_client().get_or_create_collection(name="legal_knowledge_base")
def get_case_kb_collection(uid: str) -> Collection: return get_client().get_or_create_collection(name=f"user_{uid}")

def query_global_knowledge_base(text: str, n_results: int = 10, jurisdiction: str = 'ks') -> List[Dict[str, Any]]:
    from . import embedding_service
    emb = embedding_service.generate_embedding(text)
    if not emb: return []
    try:
        res = get_global_collection().query(query_embeddings=[emb], n_results=n_results, where={"jurisdiction": jurisdiction})
        return [{"text": d, "source": m.get("source", "Ligji"), " law_title": m.get("law_title"), "article_number": m.get("article_number"), "type": "GLOBAL_LAW", "chunk_id": i} 
                for d, m, i in zip(res['documents'][0], res['metadatas'][0], res['ids'][0])] if res.get('documents') else []
    except Exception: return []

def query_case_knowledge_base(uid: str, text: str, n_results: int = 15, **kwargs) -> List[Dict[str, Any]]:
    from . import embedding_service
    emb = embedding_service.generate_embedding(text)
    if not emb: return []
    try:
        res = get_case_kb_collection(uid).query(query_embeddings=[emb], n_results=n_results)
        return [{"text": d, "source": m.get("file_name", "Doc"), "page": m.get("page", "N/A"), "type": "CASE_FACT"} 
                for d, m in zip(res['documents'][0], res['metadatas'][0])] if res.get('documents') else []
    except Exception: return []

def create_and_store_embeddings_from_chunks(uid: str, did: str, cid: str, fname: str, chunks: List[str], metas: Sequence[Dict[str, Any]]) -> bool:
    from . import embedding_service
    try:
        coll = get_case_kb_collection(uid)
        embeddings, valid_chunks, valid_metas = [], [], []
        for i, chunk in enumerate(chunks):
            emb = embedding_service.generate_embedding(chunk)
            if emb:
                embeddings.append(emb); valid_chunks.append(chunk)
                valid_metas.append(_sanitize_metadata({**metas[i], "source_document_id": str(did), "case_id": str(cid), "file_name": fname, "owner_id": str(uid)}))
        if embeddings:
            coll.add(embeddings=embeddings, documents=valid_chunks, metadatas=valid_metas, ids=[f"{did}_{int(time.time())}_{i}" for i in range(len(valid_chunks))])
            return True
    except Exception as e: logger.error(f"Ingestion failed: {e}")
    return False

def delete_document_embeddings(uid: str, did: str):
    try: get_case_kb_collection(uid).delete(where={"source_document_id": str(did)})
    except Exception: pass

def delete_user_collection(uid: str):
    try: get_client().delete_collection(name=f"user_{uid}")
    except Exception: pass

def update_document_metadata(uid: str, did: str, meta: Dict[str, Any]):
    try:
        coll = get_case_kb_collection(uid)
        res = coll.get(where={"source_document_id": str(did)})
        if res.get('ids'): coll.update(ids=res['ids'], metadatas=[_sanitize_metadata({**m, **meta}) for m in res['metadatas']])
    except Exception: pass

def copy_document_embeddings(sid: str, tid: str, tuid: str, tcid: str):
    try:
        coll = get_case_kb_collection(tuid)
        res = coll.get(where={"source_document_id": str(sid)}, include=["embeddings", "documents", "metadatas"])
        if res.get('ids'):
            n_ids = [f"{tid}_copy_{i}_{int(time.time())}" for i in range(len(res['ids']))]
            n_metas = [_sanitize_metadata({**m, "source_document_id": str(tid), "case_id": str(tcid)}) for m in res['metadatas']]
            coll.add(ids=n_ids, embeddings=res['embeddings'], documents=res['documents'], metadatas=n_metas)
    except Exception: pass