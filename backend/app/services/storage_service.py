# FILE: backend/app/services/storage_service.py
# PHOENIX PROTOCOL - INFINITE UPLOAD SCALING + GENERIC UTILS
# 1. Uses TransferConfig to enable Multi-Part Uploads (Chunks).
# 2. Prevents timeouts on massive legal files (100MB+).
# 3. GENERIC UTILS: Added 'upload_file_raw' and 'get_file_stream' for Business Logos.

import os
import boto3
import uuid
from botocore.client import Config
from boto3.s3.transfer import TransferConfig
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

transfer_config = TransferConfig(
    multipart_threshold=1024 * 1024 * 15, 
    max_concurrency=4,
    multipart_chunksize=1024 * 1024 * 15,
    use_threads=True
)

def get_s3_client():
    global _s3_client
    if _s3_client:
        return _s3_client
    
    if not all([B2_KEY_ID, B2_APPLICATION_KEY, B2_ENDPOINT_URL, B2_BUCKET_NAME]):
        logger.critical("!!! CRITICAL: B2 Storage service is not configured.")
        raise HTTPException(status_code=500, detail="Storage service is not configured.")

    try:
        _s3_client = boto3.client(
            's3',
            endpoint_url=B2_ENDPOINT_URL,
            aws_access_key_id=B2_KEY_ID,
            aws_secret_access_key=B2_APPLICATION_KEY,
            config=Config(signature_version='s3v4')
        )
        return _s3_client
    except Exception as e:
        logger.critical(f"!!! CRITICAL: Failed to initialize B2 client: {e}")
        raise HTTPException(status_code=500, detail="Could not initialize storage client.")

# --- GENERIC UTILS (ADDED FOR BUSINESS SERVICE) ---

def upload_file_raw(file: UploadFile, folder: str) -> str:
    """
    Generic upload for non-document files (e.g. Business Logos).
    Generates a UUID filename to prevent collisions.
    """
    s3_client = get_s3_client()
    file_extension = os.path.splitext(file.filename or "")[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    storage_key = f"{folder}/{unique_filename}"
    
    try:
        file.file.seek(0) # Reset pointer
        s3_client.upload_fileobj(
            file.file, 
            B2_BUCKET_NAME, 
            storage_key,
            Config=transfer_config
        )
        return storage_key
    except Exception as e:
        logger.error(f"Raw upload failed: {e}")
        raise e

def get_file_stream(storage_key: str) -> Any:
    """
    Generic stream retriever. Used for proxing logos/images.
    """
    s3_client = get_s3_client()
    try:
        response = s3_client.get_object(Bucket=B2_BUCKET_NAME, Key=storage_key)
        return response['Body']
    except Exception as e:
        logger.error(f"Failed to retrieve file stream: {e}")
        raise e

# --- DOCUMENT SPECIFIC FUNCTIONS ---

def upload_original_document(file: UploadFile, user_id: str, case_id: str) -> str:
    s3_client = get_s3_client()
    file_name = file.filename or "unknown_file"
    storage_key = f"{user_id}/{case_id}/{file_name}"
    
    try:
        logger.info(f"--- [Storage Service] Streaming ORIGINAL document: {storage_key} ---")
        file.file.seek(0)
        s3_client.upload_fileobj(file.file, B2_BUCKET_NAME, storage_key, Config=transfer_config)
        return storage_key
    except (BotoCoreError, ClientError) as e:
        logger.error(f"!!! ERROR: Upload failed: {storage_key}, Reason: {e}")
        raise HTTPException(status_code=500, detail="Could not upload file.")

def upload_processed_text(text_content: str, user_id: str, case_id: str, original_doc_id: str) -> str:
    s3_client = get_s3_client()
    file_name = f"{original_doc_id}_processed.txt"
    storage_key = f"{user_id}/{case_id}/processed/{file_name}"
    temp_file_path = ''
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as temp_file:
            temp_file.write(text_content)
            temp_file_path = temp_file.name

        s3_client.upload_file(temp_file_path, B2_BUCKET_NAME, storage_key)
        return storage_key
    except Exception as e:
        logger.error(f"!!! ERROR: Processed text upload failed: {e}")
        raise HTTPException(status_code=500, detail="Could not upload processed text.")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

def upload_document_preview(file_path: str, user_id: str, case_id: str, original_doc_id: str) -> str:
    s3_client = get_s3_client()
    file_name = f"{original_doc_id}_preview.pdf"
    storage_key = f"{user_id}/{case_id}/previews/{file_name}"
    
    try:
        s3_client.upload_file(file_path, B2_BUCKET_NAME, storage_key)
        return storage_key
    except Exception as e:
        logger.error(f"!!! ERROR: Preview upload failed: {e}")
        raise HTTPException(status_code=500, detail="Could not upload preview.")

def download_preview_document_stream(storage_key: str) -> Any:
    return get_file_stream(storage_key)

def download_original_document_stream(storage_key: str) -> Any:
    return get_file_stream(storage_key)

def download_processed_text(storage_key: str) -> bytes | None:
    s3_client = get_s3_client()
    try:
        response = s3_client.get_object(Bucket=B2_BUCKET_NAME, Key=storage_key)
        return response['Body'].read()
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey': return None
        raise HTTPException(status_code=500, detail="Could not download processed text.")
    except Exception:
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

def delete_file(storage_key: str):
    s3_client = get_s3_client()
    try:
        logger.info(f"--- Deleting: {storage_key} ---")
        s3_client.delete_object(Bucket=B2_BUCKET_NAME, Key=storage_key)
    except Exception as e:
        logger.error(f"!!! ERROR: Delete failed: {e}")