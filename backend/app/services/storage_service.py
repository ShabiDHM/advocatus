# FILE: backend/app/services/storage_service.py
# PHOENIX PROTOCOL - INFINITE UPLOAD SCALING
# 1. Uses TransferConfig to enable Multi-Part Uploads (Chunks).
# 2. Prevents timeouts on massive legal files (100MB+).
# 3. Optimizes memory usage using pure streaming.

import os
import boto3
from botocore.client import Config
from boto3.s3.transfer import TransferConfig # <--- THE TURBO CHARGER
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

# --- PHOENIX CONFIG: Optimized for Large Legal Bundles ---
# multipart_threshold: Files larger than 15MB are split into chunks
# max_concurrency: Upload 4 chunks at the same time (Faster)
# use_threads: True (Non-blocking)
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
        logger.info(f"--- [Storage Service] Streaming ORIGINAL document: {storage_key} ---")
        
        # Reset file pointer to beginning just in case
        file.file.seek(0)
        
        # PHOENIX FIX: Added Config=transfer_config for Multi-Part Uploads
        s3_client.upload_fileobj(
            file.file, 
            B2_BUCKET_NAME, 
            storage_key,
            Config=transfer_config
        )
        
        logger.info(f"--- [Storage Service] Successfully uploaded: {storage_key} ---")
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

        logger.info(f"--- [Storage Service] Uploading processed text: {storage_key} ---")
        s3_client.upload_file(temp_file_path, B2_BUCKET_NAME, storage_key)
        logger.info(f"--- [Storage Service] Success: {storage_key} ---")
        
        return storage_key
    except (BotoCoreError, ClientError, IOError) as e:
        logger.error(f"!!! ERROR: Failed to upload processed text. Key: {storage_key}, Reason: {e}")
        raise HTTPException(status_code=500, detail="Could not upload processed text to storage.")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

def upload_document_preview(file_path: str, user_id: str, case_id: str, original_doc_id: str) -> str:
    s3_client = get_s3_client()
    file_name = f"{original_doc_id}_preview.pdf"
    storage_key = f"{user_id}/{case_id}/previews/{file_name}"
    
    try:
        logger.info(f"--- [Storage Service] Uploading preview: {storage_key} ---")
        s3_client.upload_file(file_path, B2_BUCKET_NAME, storage_key)
        return storage_key
    except (BotoCoreError, ClientError, IOError) as e:
        logger.error(f"!!! ERROR: Failed to upload preview. Key: {storage_key}, Reason: {e}")
        raise HTTPException(status_code=500, detail="Could not upload document preview to storage.")

def download_preview_document_stream(storage_key: str) -> Any:
    s3_client = get_s3_client()
    try:
        logger.info(f"--- [Storage Service] Streaming PREVIEW: {storage_key} ---")
        response = s3_client.get_object(Bucket=B2_BUCKET_NAME, Key=storage_key)
        return response['Body']
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            logger.error(f"!!! ERROR: Preview not found: {storage_key}")
            raise HTTPException(status_code=404, detail="Preview file not found.")
        else:
            logger.error(f"!!! ERROR: Stream failed: {storage_key}, Reason: {e}")
            raise HTTPException(status_code=500, detail="Could not download preview file.")

def download_original_document_stream(storage_key: str) -> Any:
    s3_client = get_s3_client()
    try:
        logger.info(f"--- [Storage Service] Streaming ORIGINAL: {storage_key} ---")
        response = s3_client.get_object(Bucket=B2_BUCKET_NAME, Key=storage_key)
        return response['Body']
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            logger.error(f"!!! ERROR: File not found: {storage_key}")
            raise HTTPException(status_code=404, detail="File not found.")
        else:
            logger.error(f"!!! ERROR: Stream failed: {storage_key}, Reason: {e}")
            raise HTTPException(status_code=500, detail="Could not download file.")

def download_processed_text(storage_key: str) -> bytes | None:
    s3_client = get_s3_client()
    try:
        response = s3_client.get_object(Bucket=B2_BUCKET_NAME, Key=storage_key)
        return response['Body'].read()
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            return None
        logger.error(f"!!! ERROR: Download failed: {storage_key}, Reason: {e}")
        raise HTTPException(status_code=500, detail="Could not download processed text.")
    except Exception as e:
        logger.error(f"!!! ERROR: Unexpected error: {storage_key}, Reason: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

def delete_file(storage_key: str):
    s3_client = get_s3_client()
    try:
        logger.info(f"--- [Storage Service] Deleting: {storage_key} ---")
        s3_client.delete_object(Bucket=B2_BUCKET_NAME, Key=storage_key)
        logger.info(f"--- [Storage Service] Deleted: {storage_key} ---")
    except (BotoCoreError, ClientError) as e:
        logger.error(f"!!! ERROR: Delete failed: {storage_key}, Reason: {e}")