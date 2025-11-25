# FILE: backend/app/services/backup_service.py
# PHOENIX PROTOCOL - THE BLACK BOX (B2 BACKUP)
# 1. HOT BACKUP: Exports MongoDB and Neo4j without stopping services.
# 2. OFFSITE STORAGE: Uploads to Backblaze B2 via S3 protocol.
# 3. DATA INTEGRITY: JSON serializes BSON types (ObjectId, datetime) correctly.

import os
import json
import shutil
import zipfile
import boto3
import structlog
from datetime import datetime
from bson import ObjectId, json_util
from pymongo import MongoClient
from .graph_service import graph_service

logger = structlog.get_logger(__name__)

# --- CONFIGURATION ---
BACKUP_DIR = "/tmp/backups"
MONGO_URI = os.getenv("DATABASE_URI")
DB_NAME = "phoenix_protocol_db"

# B2 Credentials
B2_KEY_ID = os.getenv("B2_KEY_ID")
B2_APP_KEY = os.getenv("B2_APPLICATION_KEY")
B2_BUCKET = os.getenv("B2_BUCKET_NAME")
B2_ENDPOINT = os.getenv("B2_ENDPOINT_URL")

class BackupService:
    def __init__(self):
        os.makedirs(BACKUP_DIR, exist_ok=True)

    def _get_s3_client(self):
        return boto3.client(
            's3',
            endpoint_url=B2_ENDPOINT,
            aws_access_key_id=B2_KEY_ID,
            aws_secret_access_key=B2_APP_KEY
        )

    def _dump_mongodb(self, timestamp_dir: str):
        """Exports all collections to JSON files."""
        logger.info("💾 Starting MongoDB Dump...")
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        
        dump_path = os.path.join(timestamp_dir, "mongo")
        os.makedirs(dump_path, exist_ok=True)

        collections = db.list_collection_names()
        for col_name in collections:
            logger.info(f"   ↳ Exporting collection: {col_name}")
            cursor = db[col_name].find({})
            file_path = os.path.join(dump_path, f"{col_name}.json")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                # Use json_util to handle ObjectId and DateTime
                f.write(json_util.dumps(list(cursor), indent=2))
        
        logger.info("✅ MongoDB Dump Complete.")

    def _dump_neo4j(self, timestamp_dir: str):
        """Exports Graph Data using APOC."""
        logger.info("🕸️  Starting Neo4j Graph Dump...")
        dump_path = os.path.join(timestamp_dir, "neo4j")
        os.makedirs(dump_path, exist_ok=True)
        file_path = os.path.join(dump_path, "graph_dump.json")

        # Cypher query to export all nodes/rels
        query = """
        CALL apoc.export.json.all(null, {stream: true})
        YIELD data
        RETURN data
        """
        
        try:
            # Use the existing graph service connection
            graph_service._connect()
            if not graph_service._driver:
                logger.error("❌ Neo4j Driver unavailable. Skipping Graph Dump.")
                return

            with graph_service._driver.session() as session:
                with open(file_path, 'w', encoding='utf-8') as f:
                    result = session.run(query)
                    # Concatenate the stream parts
                    for record in result:
                        f.write(record["data"])
            
            logger.info("✅ Neo4j Dump Complete.")
        except Exception as e:
            logger.error(f"❌ Neo4j Export Failed: {e}")
            # Don't crash the whole backup if graph fails

    def perform_full_backup(self):
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        run_dir = os.path.join(BACKUP_DIR, timestamp)
        zip_filename = f"juristi_backup_{timestamp}.zip"
        zip_path = os.path.join(BACKUP_DIR, zip_filename)

        try:
            logger.info(f"🚀 Starting Backup Sequence: {timestamp}")
            
            # 1. Dump Data
            self._dump_mongodb(run_dir)
            self._dump_neo4j(run_dir)

            # 2. Compress
            logger.info("📦 Compressing Archive...")
            shutil.make_archive(run_dir, 'zip', run_dir)
            # make_archive creates file.zip, we rename/move if needed logic matches
            final_zip = run_dir + ".zip"
            
            # 3. Upload to B2
            logger.info(f"☁️  Uploading to B2 Bucket: {B2_BUCKET}...")
            s3 = self._get_s3_client()
            s3.upload_file(final_zip, B2_BUCKET, zip_filename)
            
            logger.info("✅ Upload Successful.")
            return zip_filename

        except Exception as e:
            logger.error(f"💥 CRITICAL BACKUP FAILURE: {e}")
            raise e
        finally:
            # 4. Cleanup
            logger.info("🧹 Cleaning up temp files...")
            if os.path.exists(run_dir):
                shutil.rmtree(run_dir)
            if os.path.exists(run_dir + ".zip"):
                os.remove(run_dir + ".zip")

# Global Instance
backup_service = BackupService()