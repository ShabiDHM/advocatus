# FILE: backend/app/services/storage_service.py

import os
import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import UploadFile, HTTPException
import logging
import tempfile
from typing import Any

logger = logging.getLogger(__name__)

# --- B2 Configuration ---
B2_KEY_ID = os.getenv("B2_KEY_ID")
B2_APPLICATION_KEY = os.getenv("B2_APPLICATION_KEY")
B2_ENDPOINT_URL = os.getenv("B2_ENDPOINT_URL")
B2_BUCKET_NAME = os.getenv("B2_BUCKET_NAME")

_s3_client = None

def get_s3_client():
    global _s3_client
    if _s3_client:
        return _s3_client
    
    if not all([B2_KEY_ID, B2_APPLICATION_KEY, B2_ENDPOINT_URL, B2_BUCKET_NAME]):
        logger.critical("!!! CRITICAL: B2 Storage service is not configured. Check environment variables.")
        raise HTTPException(status_code=500, detail="Storage service is not configured.")

    try:
        logger.info("--- [Storage Service] Initializing B2 client... ---")
        _s3_client = boto3.client(
            's3',
            endpoint_url=B2_ENDPOINT_URL,
            aws_access_key_id=B2_KEY_ID,
            aws_secret_access_key=B2_APPLICATION_KEY,
            config=Config(signature_version='s3v4')
        )
        logger.info("--- [Storage Service] B2 client initialized successfully. ---")
        return _s3_client
    except Exception as e:
        logger.critical(f"!!! CRITICAL: Failed to initialize B2 client. Reason: {e}")
        raise HTTPException(status_code=500, detail="Could not initialize storage client.")

def upload_original_document(file: UploadFile, user_id: str, case_id: str) -> str:
    s3_client = get_s3_client()
    file_name = file.filename or "unknown_file"
    storage_key = f"{user_id}/{case_id}/{file_name}"
    
    try:
        logger.info(f"--- [Storage Service] Uploading original document to key: {storage_key} ---")
        s3_client.upload_fileobj(file.file, B2_BUCKET_NAME, storage_key)
        logger.info(f"--- [Storage Service] Successfully uploaded original document to key: {storage_key} ---")
        return storage_key
    except (BotoCoreError, ClientError) as e:
        logger.error(f"!!! ERROR: Failed to upload original document to B2. Key: {storage_key}, Reason: {e}")
        raise HTTPException(status_code=500, detail="Could not upload file to storage.")

def upload_processed_text(text_content: str, user_id: str, case_id: str, original_doc_id: str) -> str:
    s3_client = get_s3_client()
    file_name = f"{original_doc_id}_processed.txt"
    storage_key = f"{user_id}/{case_id}/processed/{file_name}"
    temp_file_path = ''
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(text_content)
            temp_file_path = temp_file.name

        logger.info(f"--- [Storage Service] Uploading processed text from temp file to key: {storage_key} ---")
        s3_client.upload_file(temp_file_path, B2_BUCKET_NAME, storage_key)
        logger.info(f"--- [Storage Service] Successfully uploaded processed text to key: {storage_key} ---")
        
        return storage_key
    except (BotoCoreError, ClientError, IOError) as e:
        logger.error(f"!!! ERROR: Failed to upload processed text to B2. Key: {storage_key}, Reason: {e}")
        raise HTTPException(status_code=500, detail="Could not upload processed text to storage.")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

# --- PHOENIX PROTOCOL CURE: Added function for the backend worker to upload the generated PDF preview ---
def upload_document_preview(file_path: str, user_id: str, case_id: str, original_doc_id: str) -> str:
    s3_client = get_s3_client()
    file_name = f"{original_doc_id}_preview.pdf"
    storage_key = f"{user_id}/{case_id}/previews/{file_name}"
    
    try:
        logger.info(f"--- [Storage Service] Uploading document preview to key: {storage_key} ---")
        s3_client.upload_file(file_path, B2_BUCKET_NAME, storage_key)
        logger.info(f"--- [Storage Service] Successfully uploaded document preview to key: {storage_key} ---")
        return storage_key
    except (BotoCoreError, ClientError, IOError) as e:
        logger.error(f"!!! ERROR: Failed to upload document preview to B2. Key: {storage_key}, Reason: {e}")
        raise HTTPException(status_code=500, detail="Could not upload document preview to storage.")

# --- PHOENIX PROTOCOL CURE: Implemented the missing function to resolve the final error ---
def download_preview_document_stream(storage_key: str) -> Any:
    """
    Retrieves the document preview (PDF) from B2 as a streaming body object.
    This is memory-efficient and ideal for FastAPI's StreamingResponse.
    """
    s3_client = get_s3_client()
    try:
        logger.info(f"--- [Storage Service] Streaming PREVIEW file from B2 with key: {storage_key} ---")
        response = s3_client.get_object(Bucket=B2_BUCKET_NAME, Key=storage_key)
        return response['Body']
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            logger.error(f"!!! ERROR: Preview document file not found in B2. Key: {storage_key}")
            raise HTTPException(status_code=404, detail="Preview file not found in storage.")
        else:
            logger.error(f"!!! ERROR: Failed to stream preview file from B2. Key: {storage_key}, Reason: {e}")
            raise HTTPException(status_code=500, detail="Could not download preview file from storage.")

def download_original_document_stream(storage_key: str) -> Any:
    """
    Retrieves the original document from B2 as a streaming body object.
    This is memory-efficient and ideal for FastAPI's StreamingResponse.
    """
    s3_client = get_s3_client()
    try:
        logger.info(f"--- [Storage Service] Streaming ORIGINAL file from B2 with key: {storage_key} ---")
        response = s3_client.get_object(Bucket=B2_BUCKET_NAME, Key=storage_key)
        return response['Body']
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            logger.error(f"!!! ERROR: Original document file not found in B2. Key: {storage_key}")
            raise HTTPException(status_code=404, detail="File not found in storage.")
        else:
            logger.error(f"!!! ERROR: Failed to stream file from B2. Key: {storage_key}, Reason: {e}")
            raise HTTPException(status_code=500, detail="Could not download file from storage.")

def download_processed_text(storage_key: str) -> bytes | None:
    s3_client = get_s3_client()
    try:
        logger.info(f"--- [Storage Service] Downloading processed text content from key: {storage_key} ---")
        response = s3_client.get_object(Bucket=B2_BUCKET_NAME, Key=storage_key)
        content_bytes = response['Body'].read()
        logger.info(f"--- [Storage Service] Successfully downloaded processed text content from key: {storage_key} ---")
        return content_bytes
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            logger.error(f"!!! ERROR: Processed text file not found in B2. Key: {storage_key}")
            return None
        else:
            logger.error(f"!!! ERROR: Failed to download processed text from B2. Key: {storage_key}, Reason: {e}")
            raise HTTPException(status_code=500, detail="Could not download processed text from storage.")
    except (BotoCoreError, Exception) as e:
        logger.error(f"!!! ERROR: An unexpected error occurred downloading processed text from B2. Key: {storage_key}, Reason: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred downloading file from storage.")

def delete_file(storage_key: str):
    s3_client = get_s3_client()
    try:
        logger.info(f"--- [Storage Service] Deleting file from B2 with key: {storage_key} ---")
        s3_client.delete_object(Bucket=B2_BUCKET_NAME, Key=storage_key)
        logger.info(f"--- [Storage Service] Successfully deleted file from B2 with key: {storage_key} ---")
    except (BotoCoreError, ClientError) as e:
        logger.error(f"!!! ERROR: Failed to delete file from B2. Key: {storage_key}, Reason: {e}")