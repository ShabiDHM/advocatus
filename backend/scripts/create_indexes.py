# FILE: backend/scripts/create_indexes.py
# PHOENIX PROTOCOL — MongoDB Index Setup
# Krijon indeksat e nevojshëm për performancë në Atlas Free tier.
# Ekzekutohet NJË HERË (idempotent — mund të ri-ekzekutohet pa dëm).

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
ROOT_DIR = BACKEND_DIR.parent

for p in [ROOT_DIR / ".env", BACKEND_DIR / ".env"]:
    if p.exists():
        load_dotenv(p, override=True)

sys.path.insert(0, str(BACKEND_DIR))

from pymongo import MongoClient, ASCENDING

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("create_indexes")


def run():
    uri = os.getenv("DATABASE_URI")
    db_name = os.getenv("MONGO_DB_NAME", "advocatus_db")
    if not uri:
        logger.error("❌ DATABASE_URI mungon.")
        return

    client = MongoClient(uri, serverSelectionTimeoutMS=15000)
    db = client[db_name]

    # ═══════════════════════════════════════════════════════════════════════
    # user_vectors — për case queries
    # ═══════════════════════════════════════════════════════════════════════
    logger.info("📦 Duke krijuar indeksat për user_vectors...")

    uv = db["user_vectors"]

    # Kryesor: case_id + owner_id (për query_case_knowledge_base)
    idx_name = uv.create_index(
        [("case_id", ASCENDING), ("owner_id", ASCENDING)],
        name="case_owner_idx",
    )
    logger.info(f"  ✅ Krijua indeks: {idx_name}")

    # Sekondar: document_id (për delete_document_embeddings)
    idx_name = uv.create_index(
        [("document_id", ASCENDING)],
        name="document_id_idx",
    )
    logger.info(f"  ✅ Krijua indeks: {idx_name}")

    # Sekondar: owner_id + case_id (për shkresat e përdoruesit)
    idx_name = uv.create_index(
        [("owner_id", ASCENDING), ("case_id", ASCENDING)],
        name="owner_case_idx",
    )
    logger.info(f"  ✅ Krijua indeks: {idx_name}")

    # ═══════════════════════════════════════════════════════════════════════
    # legal_knowledge_base — për global queries
    # ═══════════════════════════════════════════════════════════════════════
    logger.info("📦 Duke krijuar indeksat për legal_knowledge_base...")

    lkb = db["legal_knowledge_base"]

    # Kryesor: category + is_case_law (për caselaw fetch)
    idx_name = lkb.create_index(
        [("category", ASCENDING), ("is_case_law", ASCENDING)],
        name="category_caselaw_idx",
    )
    logger.info(f"  ✅ Krijua indeks: {idx_name}")

    # Sekondar: is_article (për statute fetch)
    idx_name = lkb.create_index(
        [("is_article", ASCENDING), ("article_number", ASCENDING)],
        name="article_number_idx",
    )
    logger.info(f"  ✅ Krijua indeks: {idx_name}")

    # Sekondar: case_number (për precedent lookup)
    idx_name = lkb.create_index(
        [("case_number", ASCENDING)],
        name="case_number_idx",
    )
    logger.info(f"  ✅ Krijua indeks: {idx_name}")

    # ═══════════════════════════════════════════════════════════════════════
    # Raportim
    # ═══════════════════════════════════════════════════════════════════════
    logger.info("")
    logger.info("═" * 60)
    logger.info("✅ TË GJITHA INDEKSAT U KRIJUAN")
    logger.info("═" * 60)
    logger.info("")
    logger.info("Indeksat e user_vectors:")
    for idx in uv.list_indexes():
        logger.info(f"  • {idx['name']}: {idx['key']}")
    logger.info("")
    logger.info("Indeksat e legal_knowledge_base:")
    for idx in lkb.list_indexes():
        logger.info(f"  • {idx['name']}: {idx['key']}")


if __name__ == "__main__":
    run()