# FILE: backend/app/services/storage_service.py
# PHOENIX PROTOCOL - STORAGE SERVICE v5.1 (S3 COPY SUPPORT)
# 1. NEW: 'copy_s3_object' allows cloning files within the bucket instantly.
# 2. STATUS: Fully compatible with Archive Import logic.

import os
import boto3
import uuid
import datetime
from botocore.client import Config
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import UploadFile
from fastapi.exceptions import HTTPException
import logging
import tempfile
from typing import Any, Optional, IO

logger = logging.getLogger(__name__)

# --- B2 Configuration ---
B2_KEY_ID = os.getenv("B2_KEY_ID")
B2_APPLICATION_KEY = os.getenv("B2_APPLICATION_KEY")
B2_ENDPOINT_URL = os.getenv("B2_ENDPOINT_URL")
B2_BUCKET_NAME = os.getenv("B2_BUCKET_NAME")

_s3_client = None

# Optimization for large files
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

# --- GENERIC UTILS ---

def generate_presigned_url(storage_key: str, expiration: int = 3600) -> Optional[str]:
    """
    Generates a temporary direct link to the file.
    """
    s3 = get_s3_client()
    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': B2_BUCKET_NAME, 'Key': storage_key},
            ExpiresIn=expiration
        )
        return url
    except Exception as e:
        logger.warning(f"Failed to generate presigned URL: {e}")
        return None

def upload_file_raw(file: UploadFile, folder: str) -> str:
    """
    Generic upload for non-document files (e.g. Business Logos).
    """
    s3_client = get_s3_client()
    file_extension = os.path.splitext(file.filename or "")[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    storage_key = f"{folder}/{unique_filename}"
    
    content_type = file.content_type or 'application/octet-stream'
    
    try:
        file.file.seek(0)
        s3_client.upload_fileobj(
            file.file, 
            B2_BUCKET_NAME, 
            storage_key,
            Config=transfer_config,
            ExtraArgs={'ContentType': content_type}
        )
        return storage_key
    except Exception as e:
        logger.error(f"Raw upload failed: {e}")
        raise e

def get_file_stream(storage_key: str) -> Any:
    """
    Generic stream retriever.
    """
    s3_client = get_s3_client()
    try:
        response = s3_client.get_object(Bucket=B2_BUCKET_NAME, Key=storage_key)
        return response['Body']
    except Exception as e:
        logger.error(f"Failed to retrieve file stream: {e}")
        raise e

# --- DOCUMENT SPECIFIC FUNCTIONS ---

def upload_bytes_as_file(file_obj: IO, filename: str, user_id: str, case_id: str, content_type: str = "application/pdf") -> str:
    s3_client = get_s3_client()
    storage_key = f"{user_id}/{case_id}/{filename}"
    
    try:
        logger.info(f"--- [Storage] Uploading BYTES: {storage_key} ({content_type}) ---")
        file_obj.seek(0)
        s3_client.upload_fileobj(
            file_obj,
            B2_BUCKET_NAME,
            storage_key,
            Config=transfer_config,
            ExtraArgs={'ContentType': content_type}
        )
        return storage_key
    except (BotoCoreError, ClientError) as e:
        logger.error(f"!!! ERROR: Byte Upload failed: {storage_key}, Reason: {e}")
        raise HTTPException(status_code=500, detail="Could not upload converted file.")

def upload_original_document(file: UploadFile, user_id: str, case_id: str) -> str:
    s3_client = get_s3_client()
    file_name = file.filename or "unknown_file"
    storage_key = f"{user_id}/{case_id}/{file_name}"
    content_type = file.content_type or 'application/pdf'
    
    try:
        logger.info(f"--- [Storage] Uploading ORIGINAL: {storage_key} ({content_type}) ---")
        file.file.seek(0)
        s3_client.upload_fileobj(
            file.file, 
            B2_BUCKET_NAME, 
            storage_key, 
            Config=transfer_config,
            ExtraArgs={'ContentType': content_type}
        )
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

        s3_client.upload_file(
            temp_file_path, 
            B2_BUCKET_NAME, 
            storage_key,
            ExtraArgs={'ContentType': 'text/plain; charset=utf-8'}
        )
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
        s3_client.upload_file(
            file_path, 
            B2_BUCKET_NAME, 
            storage_key,
            ExtraArgs={'ContentType': 'application/pdf'} 
        )
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
        raise HTTPException(status_code=500, detail="Failed to delete file.")

# PHOENIX NEW: COPY FUNCTION
def copy_s3_object(source_key: str, dest_folder: str) -> str:
    """
    Copies an object within the same bucket (Server-Side Copy).
    Returns the new storage key.
    """
    s3_client = get_s3_client()
    filename = os.path.basename(source_key)
    # Ensure unique filename to prevent overwrite
    timestamp = int(datetime.datetime.now().timestamp())
    dest_key = f"{dest_folder}/{timestamp}_{filename}"
    
    try:
        copy_source = {'Bucket': B2_BUCKET_NAME, 'Key': source_key}
        s3_client.copy(copy_source, B2_BUCKET_NAME, dest_key)
        logger.info(f"--- [Storage] Copied {source_key} -> {dest_key} ---")
        return dest_key
    except Exception as e:
        logger.error(f"!!! ERROR: S3 Copy failed: {e}")
        raise HTTPException(status_code=500, detail="Storage copy failed.")