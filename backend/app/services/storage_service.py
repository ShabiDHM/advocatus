# FILE: backend/app/services/storage_service.py
# PHOENIX PROTOCOL - STORAGE SERVICE V11.0 (DEEP DIAGNOSTICS & RESILIENT B2 CLIENT)

import os
import re
import boto3
import uuid
import datetime
import unicodedata
from botocore.client import Config
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError
from fastapi import UploadFile, status
from fastapi.exceptions import HTTPException
import logging
import tempfile
from typing import Any, Optional, IO, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)

# --- B2 Configuration (Cleaned & Stripped) ---
def _clean_env(val: Optional[str]) -> str:
    if not val:
        return ""
    return str(val).strip().strip('"').strip("'")

B2_KEY_ID = _clean_env(settings.B2_KEY_ID or os.getenv("B2_KEY_ID"))
B2_APPLICATION_KEY = _clean_env(settings.B2_APPLICATION_KEY or os.getenv("B2_APPLICATION_KEY"))
B2_ENDPOINT_URL = _clean_env(settings.B2_ENDPOINT_URL or os.getenv("B2_ENDPOINT_URL")).rstrip("/")
B2_BUCKET_NAME = _clean_env(settings.B2_BUCKET_NAME or os.getenv("B2_BUCKET_NAME"))
B2_REGION_NAME = _clean_env(getattr(settings, "B2_REGION_NAME", "") or os.getenv("B2_REGION_NAME", ""))

# MAX FILE LIMIT: 50 MB
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 50))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

_s3_client = None

# Backward compatibility transfer config
transfer_config = TransferConfig(
    multipart_threshold=10 * 1024 * 1024,
    max_concurrency=4,
    multipart_chunksize=10 * 1024 * 1024,
    use_threads=True
)

def _get_b2_region() -> str:
    if B2_REGION_NAME:
        return B2_REGION_NAME
    if B2_ENDPOINT_URL:
        match = re.search(r's3\.([a-z0-9-]+)\.backblazeb2\.com', B2_ENDPOINT_URL)
        if match:
            return match.group(1)
    return "eu-central-003"

def _infer_content_type(filename: str, fallback: str = "application/octet-stream") -> str:
    ext = os.path.splitext(filename or "")[1].lower()
    mapping = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".txt": "text/plain; charset=utf-8",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }
    return mapping.get(ext, fallback)

def sanitize_filename(filename: str) -> str:
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

def _build_fresh_s3_client():
    if not all([B2_KEY_ID, B2_APPLICATION_KEY, B2_ENDPOINT_URL, B2_BUCKET_NAME]):
        logger.critical(f"!!! CRITICAL: Missing B2 Config: KeyID={bool(B2_KEY_ID)}, AppKey={bool(B2_APPLICATION_KEY)}, Endpoint={B2_ENDPOINT_URL}, Bucket={B2_BUCKET_NAME}")
        raise HTTPException(status_code=500, detail="Storage service is not configured.")

    region = _get_b2_region()

    custom_config = Config(
        signature_version='s3v4',
        region_name=region,
        connect_timeout=20,
        read_timeout=40,
        retries={'max_attempts': 2, 'mode': 'standard'}
    )
    
    session = boto3.session.Session()
    client = session.client(
        's3',
        endpoint_url=B2_ENDPOINT_URL,
        aws_access_key_id=B2_KEY_ID,
        aws_secret_access_key=B2_APPLICATION_KEY,
        region_name=region,
        config=custom_config
    )
    
    # Test Connectivity Diagnostic
    try:
        client.head_bucket(Bucket=B2_BUCKET_NAME)
        logger.info(f"✅ [B2 Diagnostic] Bucket '{B2_BUCKET_NAME}' verified successfully on endpoint '{B2_ENDPOINT_URL}'.")
    except ClientError as ce:
        err_code = ce.response.get('Error', {}).get('Code', 'Unknown')
        logger.error(f"⚠️ [B2 Diagnostic ClientError] Bucket '{B2_BUCKET_NAME}' status check failed with Code: {err_code} ({ce})")
    except Exception as ex:
        logger.error(f"⚠️ [B2 Diagnostic Exception] Could not reach B2 Bucket: {ex}")
        
    return client

def get_s3_client(force_refresh: bool = False):
    global _s3_client
    if _s3_client is None or force_refresh:
        _s3_client = _build_fresh_s3_client()
    return _s3_client

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

def upload_bytes_as_file(file_obj: Any, filename: str, user_id: str, case_id: str, content_type: Optional[str] = None) -> str:
    clean_filename = sanitize_filename(filename)
    prefix = f"{user_id}/{case_id}".strip("/")
    storage_key = f"{prefix}/{clean_filename}" if prefix else clean_filename
    resolved_content_type = content_type or _infer_content_type(filename, "application/pdf")
    
    try:
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)
            data = file_obj.read()
        elif isinstance(file_obj, (bytes, bytearray)):
            data = bytes(file_obj)
        else:
            data = bytes(file_obj)

        if isinstance(data, str):
            data = data.encode('utf-8')
            
        check_file_size_bytes(len(data))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed reading bytes for upload: {e}")
        raise HTTPException(status_code=500, detail="Could not read upload payload.")

    logger.info(f"--- [Storage] Uploading BYTES: {storage_key} ({resolved_content_type}, {len(data) / 1024:.1f} KB) ---")
    
    for attempt in range(2):
        try:
            client = get_s3_client(force_refresh=(attempt > 0))
            client.put_object(
                Bucket=B2_BUCKET_NAME,
                Key=storage_key,
                Body=data,
                ContentType=resolved_content_type,
                ContentLength=len(data)
            )
            logger.info(f"✅ [Storage] Successfully uploaded {storage_key}")
            return storage_key
        except (BotoCoreError, ClientError) as e:
            logger.warning(f"⚠️ [Storage] Upload attempt {attempt + 1} failed: {e}")
            if attempt == 1:
                logger.error(f"!!! ERROR: Byte Upload failed permanently: {storage_key}, Reason: {e}")
                raise HTTPException(status_code=500, detail="Could not upload converted file.")

    raise HTTPException(status_code=500, detail="Could not upload converted file.")

def upload_original_document(file: UploadFile, user_id: str, case_id: str) -> str:
    clean_filename = sanitize_filename(file.filename or "document")
    content_type = file.content_type or _infer_content_type(file.filename or "", 'application/pdf')
    return upload_bytes_as_file(file.file, clean_filename, user_id, case_id, content_type)

def upload_file_raw(file: UploadFile, folder: str) -> str:
    clean_folder = sanitize_filename(folder)
    file_extension = os.path.splitext(file.filename or "")[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    content_type = file.content_type or _infer_content_type(file.filename or "")
    return upload_bytes_as_file(file.file, unique_filename, clean_folder, "", content_type)

def upload_file_from_path(file_path: str, filename: str, user_id: str, case_id: str, content_type: Optional[str] = None) -> str:
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File path does not exist.")
    with open(file_path, "rb") as f:
        data = f.read()
    return upload_bytes_as_file(data, filename, user_id, case_id, content_type)

def get_file_stream(storage_key: str) -> Any:
    for attempt in range(2):
        try:
            s3_client = get_s3_client(force_refresh=(attempt > 0))
            response = s3_client.get_object(Bucket=B2_BUCKET_NAME, Key=storage_key)
            return response['Body']
        except Exception as e:
            if attempt == 1:
                logger.error(f"Failed to retrieve file stream: {e}")
                raise HTTPException(status_code=404, detail="File not found in storage.")

def get_file_stream_with_meta(storage_key: str) -> Tuple[Any, int]:
    for attempt in range(2):
        try:
            s3_client = get_s3_client(force_refresh=(attempt > 0))
            response = s3_client.get_object(Bucket=B2_BUCKET_NAME, Key=storage_key)
            content_length = response.get('ContentLength', 0)
            return response['Body'], content_length
        except Exception as e:
            if attempt == 1:
                logger.error(f"Failed to retrieve file stream with meta: {e}")
                raise HTTPException(status_code=404, detail="File not found in storage.")

def upload_processed_text(text_content: str, user_id: str, case_id: str, original_doc_id: str) -> str:
    clean_doc_id = sanitize_filename(original_doc_id)
    file_name = f"{clean_doc_id}_processed.txt"
    data = text_content.encode('utf-8')
    return upload_bytes_as_file(data, file_name, user_id, f"{case_id}/processed", "text/plain; charset=utf-8")

def upload_document_preview(file_path: str, user_id: str, case_id: str, original_doc_id: str) -> str:
    clean_doc_id = sanitize_filename(original_doc_id)
    file_name = f"{clean_doc_id}_preview.pdf"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Preview file path does not exist.")
    with open(file_path, "rb") as f:
        data = f.read()
    return upload_bytes_as_file(data, file_name, user_id, f"{case_id}/previews", "application/pdf")

def download_preview_document_stream(storage_key: str) -> Any:
    return get_file_stream(storage_key)

def download_original_document_stream(storage_key: str) -> Any:
    return get_file_stream(storage_key)

def download_processed_text(storage_key: str) -> bytes | None:
    for attempt in range(2):
        try:
            s3_client = get_s3_client(force_refresh=(attempt > 0))
            response = s3_client.get_object(Bucket=B2_BUCKET_NAME, Key=storage_key)
            return response['Body'].read()
        except ClientError as e:
            if e.response.get('Error', {}).get('Code') == 'NoSuchKey': 
                return None
            if attempt == 1:
                raise HTTPException(status_code=500, detail="Could not download processed text.")
        except Exception:
            if attempt == 1:
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