# backend/app/services/search_service.py
# DEFINITIVE MONGODB VERSION 2.1: Corrects return type to match endpoint.

import httpx
import asyncio
from typing import List, Optional
from pymongo.database import Database
from bson import ObjectId

from . import vector_store_service, case_service
from ..models.user import UserInDB
from ..models.document import DocumentOut # Import the DocumentOut model

EMBEDDING_SERVICE_URL = "http://embedding-service:9000/generate"

async def _get_embedding_for_query(text_content: str) -> List[float]:
    """Helper to call the embedding microservice."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(EMBEDDING_SERVICE_URL, json={"text_content": text_content}, timeout=60.0)
            response.raise_for_status()
            return response.json()['embedding']
        except httpx.RequestError as e:
            raise RuntimeError(f"The embedding service is currently unavailable: {e}")

async def perform_semantic_search(query_text: str, user: UserInDB, db: Database, case_ids: Optional[List[str]] = None) -> List[DocumentOut]:
    """
    Orchestrates a cross-case semantic search and returns a list of DocumentOut models.
    """
    try:
        query_embedding = await _get_embedding_for_query(query_text)
    except RuntimeError:
        return []

    if not case_ids:
        user_cases = case_service.get_cases_for_user(owner=user, db=db)
        search_case_ids = [case['id'] for case in user_cases]
        if not search_case_ids:
            return []
    else:
        search_case_ids = case_ids

    # Step 1: Get document IDs from the vector store
    search_results = vector_store_service.query_across_cases(
        embedding=query_embedding,
        case_ids=search_case_ids,
        n_results=10
    )
    
    if not search_results:
        return []

    # Step 2: Extract the unique document IDs from the search results
    document_ids = list(set(result['document_id'] for result in search_results))
    doc_obj_ids = [ObjectId(doc_id) for doc_id in document_ids]

    # Step 3: Fetch the full document records from MongoDB
    documents_cursor = db.documents.find({"_id": {"$in": doc_obj_ids}})
    
    # Step 4: Convert the MongoDB documents into DocumentOut Pydantic models
    # Also, create a dictionary for easy lookup to preserve the search result order
    documents_map = {str(doc["_id"]): DocumentOut.model_validate(doc) for doc in documents_cursor}
    
    # Step 5: Reconstruct the list in the order returned by the semantic search
    final_results = [documents_map[doc_id] for doc_id in document_ids if doc_id in documents_map]

    return final_results

# --- DEFINITIVE FIX: Updated the sync wrapper to match the new async return type ---
def perform_search(query: str, user: UserInDB, db: Database) -> List[DocumentOut]:
    """
    Synchronous wrapper for the semantic search functionality, called by the endpoint.
    """
    return asyncio.run(perform_semantic_search(query_text=query, user=user, db=db))