# FILE: backend/scripts/precedent_ops/cluster_phase3.py
# PHOENIX PROTOCOL - TOPIC CLUSTERING PHASE 3 (UPDATE MONGODB)

import os
import sys
import json
import time
import logging
from pathlib import Path

# Shto backend/ ne sys.path
_SCRIPT_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _SCRIPT_DIR.parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from pymongo import MongoClient, UpdateOne

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("update")

from app.core.config import settings

ASSIGNMENTS_FILE = "_cluster_assignments.json"
LABELS_FILE = "_cluster_labels.json"
BATCH_SIZE = 50
LEGAL_KB = "legal_knowledge_base"


def _get_dedicated_db():
    uri = settings.DATABASE_URI or os.getenv("DATABASE_URI")
    db_name = settings.MONGO_DB_NAME or os.getenv("MONGO_DB_NAME", "advocatus_db")
    if not uri:
        raise ValueError("DATABASE_URI mungon")
    client = MongoClient(
        uri,
        socketTimeoutMS=120000,
        connectTimeoutMS=30000,
        serverSelectionTimeoutMS=30000,
    )
    return client, client[db_name]


def main():
    if not os.path.exists(ASSIGNMENTS_FILE):
        log.error(f"{ASSIGNMENTS_FILE} mungon.")
        return
    if not os.path.exists(LABELS_FILE):
        log.error(f"{LABELS_FILE} mungon.")
        return

    log.info(f"Duke lexuar {ASSIGNMENTS_FILE}...")
    with open(ASSIGNMENTS_FILE, "r", encoding="utf-8") as f:
        assignments = json.load(f)

    log.info(f"Duke lexuar {LABELS_FILE}...")
    with open(LABELS_FILE, "r", encoding="utf-8") as f:
        labels = json.load(f)

    labels_norm = {}
    for k, v in labels.items():
        try:
            labels_norm[int(k)] = v
        except (ValueError, TypeError):
            pass

    log.info(f"{len(assignments)} assignments, {len(labels_norm)} labels")

    client, db = _get_dedicated_db()
    try:
        coll = db[LEGAL_KB]

        log.info("Duke ndertuar bulk updates...")
        ops = []
        skipped = 0

        for chunk_id, info in assignments.items():
            tid = info["topic_id"]
            dist = info["distance"]
            label_info = labels_norm.get(tid)

            if not label_info:
                skipped += 1
                continue

            update = {
                "$set": {
                    "topic_id": int(tid),
                    "topic_label": label_info.get("label", ""),
                    "topic_distance": float(dist),
                    "topic_keywords": label_info.get("keywords", []),
                }
            }
            ops.append(UpdateOne({"chunk_id": chunk_id}, update))

        log.info(f"{len(ops)} operations ndertuar ({skipped} skipped)")

        log.info(f"Duke aplikuar updates ne batches te {BATCH_SIZE}...")
        t0 = time.time()
        total_modified = 0
        total_matched = 0

        for i in range(0, len(ops), BATCH_SIZE):
            batch = ops[i:i + BATCH_SIZE]
            try:
                result = coll.bulk_write(batch, ordered=False)
                total_modified += result.modified_count
                total_matched += result.matched_count
                if (i // BATCH_SIZE) % 10 == 0:
                    log.info(f"  ... {i + len(batch)}/{len(ops)} (modified={total_modified})")
            except Exception as e:
                log.error(f"Batch {i // BATCH_SIZE} deshtoi: {e}")
                continue

        elapsed = round(time.time() - t0, 1)

        print()
        print("=" * 70)
        print("UPDATE PERFUNDOI")
        print("=" * 70)
        print(f"  Matched:  {total_matched}")
        print(f"  Modified: {total_modified}")
        print(f"  Koha:     {elapsed}s")
    finally:
        client.close()


if __name__ == "__main__":
    main()