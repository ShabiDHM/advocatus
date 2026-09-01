# FILE: backend/app/services/storage_service.py
# PHOENIX PROTOCOL - STORAGE SERVICE V8.0 (ENTERPRISE RESILIENCE & B2 DIRECT PUT_OBJECT)

import os
import re
import boto3
import uuid
import datetime
import unicodedata
from botocore.client import Config
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import UploadFile, status
from fastapi.exceptions import HTTPException
import logging
import tempfile
from typing import Any, Optional, IO, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)

# --- B2 Configuration ---
B2_KEY_ID = settings.B2_KEY_ID or os.getenv("B2_KEY_ID")
B2_APPLICATION_KEY = settings.B2_APPLICATION_KEY or os.getenv("B2_APPLICATION_KEY")
B2_ENDPOINT_URL = settings.B2_ENDPOINT_URL or os.getenv("B2_ENDPOINT_URL")
B2_BUCKET_NAME = settings.B2_BUCKET_NAME or os.getenv("B2_BUCKET_NAME")

# MAX FILE LIMIT: 50 MB
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 50))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

_s3_client = None

# TransferConfig standard për ngarkime skedarësh të mëdhenj nga disku
transfer_config = TransferConfig(
    multipart_threshold=10 * 1024 * 1024,  # 10MB threshold
    max_concurrency=4,
    multipart_chunksize=10 * 1024 * 1024,
    use_threads=True
)

def sanitize_filename(filename: str) -> str:
    """
    Pastron emrin e skedarit për Backblaze:
    - Kthen shkronjat shqipe (Ë->E, Ç->C, ë->e, ç->c)
    - Zëvendëson hapësirat me '_'
    - Heq karakteret speciale
    """
    if not filename:
        return f"file_{uuid.uuid4().hex[:8]}"
    
    replacements = {
        'Ë': 'E', 'ë': 'e',
        'Ç': 'C', 'ç': 'c'
    }
    for search, replace in replacements.items():
        filename = filename.replace(search, replace)
    
    filename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore').decode('utf-8')
    clean = re.sub(r'[\s\r\n\t\*\"\'<>:\\/\|\?,]', '_', filename).strip()
    clean = re.sub(r'_+', '_', clean)
    
    if len(clean) > 80:
        base, ext = os.path.splitext(clean)
        clean = f"{base[:50]}_{uuid.uuid4().hex[:6]}{ext[:8] if ext else ''}"
    
    return clean or f"file_{uuid.uuid4().hex[:8]}"

def check_file_size_bytes(size: int):
    if size > MAX_FILE_SIZE_BYTES:
        logger.error(f"!!! REFUSED: File size ({size / (1024*1024):.2f} MB) exceeds limit of {MAX_FILE_SIZE_MB} MB.")
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Skedari është shumë i madh. Limiti maksimal është {MAX_FILE_SIZE_MB} MB."
        )

def get_s3_client():
    global _s3_client
    if _s3_client is not None:
        return _s3_client
    
    if not all([B2_KEY_ID, B2_APPLICATION_KEY, B2_ENDPOINT_URL, B2_BUCKET_NAME]):
        logger.critical("!!! CRITICAL: B2 Storage credentials or endpoint are missing.")
        raise HTTPException(status_code=500, detail="Storage service is not configured.")

    try:
        # PHOENIX FIX V8.0: Robust B2 Connection Configuration
        custom_config = Config(
            signature_version='s3v4',
            connect_timeout=30,
            read_timeout=60,
            max_pool_connections=50,
            retries={
                'max_attempts': 5,
                'mode': 'adaptive'
            },
            tcp_keepalive=True
        )
        
        _s3_client = boto3.client(
            's3',
            endpoint_url=B2_ENDPOINT_URL,
            aws_access_key_id=B2_KEY_ID,
            aws_secret_access_key=B2_APPLICATION_KEY,
            config=custom_config
        )
        logger.info("✅ S3/Backblaze B2 client successfully initialized.")
        return _s3_client
    except Exception as e:
        logger.critical(f"!!! CRITICAL: Failed to initialize S3 client: {e}")
        _s3_client = None
        raise HTTPException(status_code=500, detail="Could not initialize storage client.")

# --- GENERIC UTILS ---

def generate_presigned_url(storage_key: str, expiration: int = 3600) -> Optional[str]:
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
    s3_client = get_s3_client()
    clean_folder = sanitize_filename(folder)
    
    file_extension = os.path.splitext(file.filename or "")[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    storage_key = f"{clean_folder}/{unique_filename}"
    
    content_type = file.content_type or 'application/octet-stream'
    
    try:
        data = file.file.read()
        check_file_size_bytes(len(data))

        s3_client.put_object(
            Bucket=B2_BUCKET_NAME,
            Key=storage_key,
            Body=data,
            ContentType=content_type,
            ContentLength=len(data)
        )
        return storage_key
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Raw upload failed: {e}")
        raise HTTPException(status_code=500, detail="Raw upload failed.")

def upload_file_from_path(file_path: str, filename: str, user_id: str, case_id: str, content_type: str = "application/octet-stream") -> str:
    s3_client = get_s3_client()
    clean_filename = sanitize_filename(filename)
    storage_key = f"{user_id}/{case_id}/{clean_filename}"
    
    try:
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File path does not exist.")
        
        file_size = os.path.getsize(file_path)
        check_file_size_bytes(file_size)

        logger.info(f"--- [Storage] Uploading FILE PATH: {storage_key} ({file_size / 1024:.1f} KB) ---")
        
        with open(file_path, "rb") as f:
            data = f.read()

        s3_client.put_object(
            Bucket=B2_BUCKET_NAME,
            Key=storage_key,
            Body=data,
            ContentType=content_type,
            ContentLength=len(data)
        )
        return storage_key
    except HTTPException:
        raise
    except (BotoCoreError, ClientError) as e:
        logger.error(f"!!! ERROR: File Path Upload failed: {storage_key}, Reason: {e}")
        raise HTTPException(status_code=500, detail="Could not upload file from path.")

def get_file_stream(storage_key: str) -> Any:
    s3_client = get_s3_client()
    try:
        response = s3_client.get_object(Bucket=B2_BUCKET_NAME, Key=storage_key)
        return response['Body']
    except Exception as e:
        logger.error(f"Failed to retrieve file stream: {e}")
        raise HTTPException(status_code=404, detail="File not found in storage.")

def get_file_stream_with_meta(storage_key: str) -> Tuple[Any, int]:
    s3_client = get_s3_client()
    try:
        response = s3_client.get_object(Bucket=B2_BUCKET_NAME, Key=storage_key)
        content_length = response.get('ContentLength', 0)
        return response['Body'], content_length
    except Exception as e:
        logger.error(f"Failed to retrieve file stream with meta: {e}")
        raise HTTPException(status_code=404, detail="File not found in storage.")

# --- DOCUMENT SPECIFIC FUNCTIONS ---

def upload_bytes_as_file(file_obj: IO, filename: str, user_id: str, case_id: str, content_type: str = "application/pdf") -> str:
    """
    PHOENIX FIX V8.0:
    Reads entire bytes buffer and executes direct put_object with explicit ContentLength.
    Completely eliminates connection closed errors caused by streaming chunk mismatches on Backblaze B2.
    """
    s3_client = get_s3_client()
    clean_filename = sanitize_filename(filename)
    storage_key = f"{user_id}/{case_id}/{clean_filename}"
    
    try:
        file_obj.seek(0)
        data = file_obj.read()
        
        # If read returned str instead of bytes
        if isinstance(data, str):
            data = data.encode('utf-8')
            
        check_file_size_bytes(len(data))

        logger.info(f"--- [Storage] Uploading BYTES (direct put): {storage_key} ({len(data) / 1024:.1f} KB) ---")
        
        s3_client.put_object(
            Bucket=B2_BUCKET_NAME,
            Key=storage_key,
            Body=data,
            ContentType=content_type,
            ContentLength=len(data)
        )
        return storage_key
    except HTTPException:
        raise
    except (BotoCoreError, ClientError) as e:
        logger.error(f"!!! ERROR: Byte Upload failed: {storage_key}, Reason: {e}")
        raise HTTPException(status_code=500, detail="Could not upload converted file.")

def upload_original_document(file: UploadFile, user_id: str, case_id: str) -> str:
    s3_client = get_s3_client()
    clean_filename = sanitize_filename(file.filename or "document")
    storage_key = f"{user_id}/{case_id}/{clean_filename}"
    content_type = file.content_type or 'application/pdf'
    
    try:
        file.file.seek(0)
        data = file.file.read()
        check_file_size_bytes(len(data))

        logger.info(f"--- [Storage] Uploading ORIGINAL: {storage_key} ({len(data) / 1024:.1f} KB) ---")
        
        s3_client.put_object(
            Bucket=B2_BUCKET_NAME,
            Key=storage_key,
            Body=data,
            ContentType=content_type,
            ContentLength=len(data)
        )
        return storage_key
    except HTTPException:
        raise
    except (BotoCoreError, ClientError) as e:
        logger.error(f"!!! ERROR: Upload failed: {storage_key}, Reason: {e}")
        raise HTTPException(status_code=500, detail="Could not upload file.")

def upload_processed_text(text_content: str, user_id: str, case_id: str, original_doc_id: str) -> str:
    s3_client = get_s3_client()
    clean_doc_id = sanitize_filename(original_doc_id)
    file_name = f"{clean_doc_id}_processed.txt"
    storage_key = f"{user_id}/{case_id}/processed/{file_name}"
    
    try:
        data = text_content.encode('utf-8')
        check_file_size_bytes(len(data))
        
        s3_client.put_object(
            Bucket=B2_BUCKET_NAME,
            Key=storage_key,
            Body=data,
            ContentType='text/plain; charset=utf-8',
            ContentLength=len(data)
        )
        return storage_key
    except Exception as e:
        logger.error(f"!!! ERROR: Processed text upload failed: {e}")
        raise HTTPException(status_code=500, detail="Could not upload processed text.")

def upload_document_preview(file_path: str, user_id: str, case_id: str, original_doc_id: str) -> str:
    s3_client = get_s3_client()
    clean_doc_id = sanitize_filename(original_doc_id)
    file_name = f"{clean_doc_id}_preview.pdf"
    storage_key = f"{user_id}/{case_id}/previews/{file_name}"
    
    try:
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Preview file path does not exist.")
            
        with open(file_path, "rb") as f:
            data = f.read()
            
        s3_client.put_object(
            Bucket=B2_BUCKET_NAME,
            Key=storage_key,
            Body=data,
            ContentType='application/pdf',
            ContentLength=len(data)
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
        if e.response.get('Error', {}).get('Code') == 'NoSuchKey': 
            return None
        raise HTTPException(status_code=500, detail="Could not download processed text.")
    except Exception:
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

def delete_file(storage_key: str):
    if not storage_key or '\n' in storage_key or '**' in storage_key or len(storage_key) > 300:
        logger.warning(f"[Storage Guard] Bllokuar thirrja delete për çelës të parregullt: {str(storage_key)[:60]}...")
        return

    s3_client = get_s3_client()
    try:
        logger.info(f"--- [Total Wipeout] Deleting: {storage_key} ---")
        
        versions = s3_client.list_object_versions(Bucket=B2_BUCKET_NAME, Prefix=storage_key)
        
        if 'Versions' in versions:
            for version in versions['Versions']:
                if version['Key'] == storage_key:
                    s3_client.delete_object(
                        Bucket=B2_BUCKET_NAME, 
                        Key=storage_key, 
                        VersionId=version['VersionId']
                    )
                    
        if 'DeleteMarkers' in versions:
            for marker in versions['DeleteMarkers']:
                if marker['Key'] == storage_key:
                    s3_client.delete_object(
                        Bucket=B2_BUCKET_NAME, 
                        Key=storage_key, 
                        VersionId=marker['VersionId']
                    )
                    
        s3_client.delete_object(Bucket=B2_BUCKET_NAME, Key=storage_key)
        logger.info("✅ Skedari u fshi përfundimisht nga hapësira ruajtëse.")

    except Exception as e:
        logger.error(f"!!! ERROR: Delete failed for {storage_key}: {e}")
        pass

def copy_s3_object(source_key: str, dest_folder: str) -> str:
    s3_client = get_s3_client()
    filename = os.path.basename(source_key)
    clean_filename = sanitize_filename(filename)
    timestamp = int(datetime.datetime.now().timestamp())
    dest_key = f"{dest_folder}/{timestamp}_{clean_filename}"
    
    try:
        copy_source = {'Bucket': B2_BUCKET_NAME, 'Key': source_key}
        s3_client.copy(copy_source, B2_BUCKET_NAME, dest_key)
        logger.info(f"--- [Storage] Copied {source_key} -> {dest_key} ---")
        return dest_key
    except Exception as e:
        logger.error(f"!!! ERROR: S3 Copy failed: {e}")
        raise HTTPException(status_code=500, detail="Storage copy failed.")