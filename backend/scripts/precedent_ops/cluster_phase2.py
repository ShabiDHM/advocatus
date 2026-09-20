# -*- coding: utf-8 -*-
"""Shtresa 2.1 - Faza 2: etiketon cluster-et me LLM."""
import os
import json
import time
import logging
import numpy as np

from pymongo import MongoClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("labels")

from app.core.config import settings

K = 25
SAMPLES_PER_CLUSTER = 8
MAX_CHARS_PER_SAMPLE = 400

ASSIGNMENTS_FILE = "_cluster_assignments.json"
CENTROIDS_FILE = "_cluster_centroids.npz"
LABELS_FILE = "_cluster_labels.json"
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


def _get_representative_texts(db, assignments):
    """Per cdo cluster, merr SAMPLES_PER_CLUSTER dokumentet me te afert me centroid."""
    coll = db[LEGAL_KB]

    by_topic = {}
    for chunk_id, info in assignments.items():
        tid = info["topic_id"]
        dist = info["distance"]
        by_topic.setdefault(tid, []).append((dist, chunk_id))

    samples_by_topic = {}
    all_chunk_ids = []

    for tid, items in by_topic.items():
        items.sort(key=lambda x: x[0])
        selected = items[:SAMPLES_PER_CLUSTER]
        samples_by_topic[tid] = [c for _, c in selected]
        all_chunk_ids.extend([c for _, c in selected])

    log.info(f"Duke terhequr {len(all_chunk_ids)} tekste nga DB...")
    docs = list(coll.find(
        {"chunk_id": {"$in": all_chunk_ids}},
        {"chunk_id": 1, "text": 1, "case_number": 1, "source": 1}
    ))

    text_by_id = {}
    for d in docs:
        cid = str(d.get("chunk_id"))
        txt = (d.get("text") or "")[:MAX_CHARS_PER_SAMPLE]
        cn = d.get("case_number") or "?"
        text_by_id[cid] = (cn, txt)

    result = {}
    for tid, chunk_ids in samples_by_topic.items():
        result[tid] = []
        for cid in chunk_ids:
            if cid in text_by_id:
                result[tid].append(text_by_id[cid])

    return result


def _label_cluster(topic_id, samples):
    """Thirr DeepSeek per te etiketuar nje cluster."""
    from app.services.llm.llm_client import _call_llm, clean_and_parse_json, DEEP_ANALYSIS_MODEL

    sys_p = """Ti je ekspert i jurisprudences se Gjykates Supreme te Kosoves.

DETYRA: Duke u bazuar ne shembujt e dhene, jep:
  1. label: etikete e shkurter 3-6 fjale (shqip)
  2. keywords: 5-8 fjale kyce (shqip)
  3. description: 1 fjali pershkrim

Kthe VETEM JSON:
{"label": "...", "keywords": ["...", "..."], "description": "..."}
"""

    user_p = f"CLUSTER ID: {topic_id}\n\nSHEMBUJ ({len(samples)} dokumente):\n\n"
    for i, (cn, txt) in enumerate(samples, 1):
        user_p += f"[{i}] {cn}\n{txt}\n\n"

    raw = _call_llm(sys_p, user_p, json_mode=True, model=DEEP_ANALYSIS_MODEL)
    if not raw:
        return None

    parsed = clean_and_parse_json(raw)
    if not parsed or "label" not in parsed:
        return None

    return {
        "topic_id": topic_id,
        "label": str(parsed.get("label", "")).strip(),
        "keywords": parsed.get("keywords", []),
        "description": str(parsed.get("description", "")).strip(),
    }


def main():
    if not os.path.exists(ASSIGNMENTS_FILE):
        log.error(f"{ASSIGNMENTS_FILE} mungon. Ekzekuto _cluster_phase1.py para.")
        return

    if os.path.exists(LABELS_FILE):
        log.info(f"{LABELS_FILE} ekziston. Fshije per ri-ekzekutim.")
        return

    log.info(f"Duke lexuar {ASSIGNMENTS_FILE}...")
    with open(ASSIGNMENTS_FILE, "r", encoding="utf-8") as f:
        assignments = json.load(f)
    log.info(f"{len(assignments)} assignments")

    client, db = _get_dedicated_db()
    try:
        log.info("Duke gjetur dokumentet representative per cdo cluster...")
        samples_by_topic = _get_representative_texts(db, assignments)
        log.info(f"Gjetur samples per {len(samples_by_topic)} cluster-e")

        labels = {}
        for tid in sorted(samples_by_topic.keys()):
            samples = samples_by_topic[tid]
            log.info(f"Etiketim topic {tid} ({len(samples)} samples)...")
            t0 = time.time()
            result = _label_cluster(tid, samples)
            elapsed = round(time.time() - t0, 1)

            if result:
                labels[tid] = result
                log.info(f"   OK: {result['label']} ({elapsed}s)")
            else:
                log.warning(f"   Deshtoi per topic {tid}")

        with open(LABELS_FILE, "w", encoding="utf-8") as f:
            json.dump(labels, f, ensure_ascii=False, indent=2)

        print()
        print("=" * 70)
        print("ETIKETAT E CLUSTER-EVE")
        print("=" * 70)
        for tid in sorted(labels.keys()):
            info = labels[tid]
            kws = ", ".join(info.get("keywords", [])[:4])
            print(f"  [{tid:2d}] {info['label']}")
            print(f"         ({kws})")
            print(f"         {info.get('description', '')}")

        print()
        print(f"Faza 2 perfundoi. Output: {LABELS_FILE}")
        print(f"Hapi tjeter: python _cluster_phase3.py")
    finally:
        client.close()


if __name__ == "__main__":
    main()