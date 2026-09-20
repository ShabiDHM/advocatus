# -*- coding: utf-8 -*-
"""Shtresa 2.1 - Faza 1: K-means clustering mbi caselaw embeddings."""
import os
import json
import time
import logging
import numpy as np

from pymongo import MongoClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("cluster")

from app.core.config import settings

K = 25
RANDOM_STATE = 42
CACHE_EMB = "_cluster_embeddings_cache.npz"
ASSIGNMENTS_FILE = "_cluster_assignments.json"
CENTROIDS_FILE = "_cluster_centroids.npz"
LEGAL_KB = "legal_knowledge_base"
EMBEDDING_DIM = 1536


def _get_dedicated_db():
    """Client i vecante me timeout te gjate (per operacione te medha)."""
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


def _fetch_embeddings(db):
    if os.path.exists(CACHE_EMB):
        log.info(f"Cache ekziston: {CACHE_EMB} - po lexoj...")
        data = np.load(CACHE_EMB, allow_pickle=True)
        embeddings = data["embeddings"]
        chunk_ids = list(data["chunk_ids"])
        log.info(f"Lexuar {len(chunk_ids)} embeddings nga cache")
        return embeddings, chunk_ids

    log.info("Duke terhequr embeddings nga MongoDB (caselaw)...")
    log.info("  batch_size=5, socketTimeout=120s")
    coll = db[LEGAL_KB]

    cursor = coll.find(
        {"category": "caselaw", "embedding": {"$exists": True, "$ne": []}},
        {"embedding": 1, "chunk_id": 1, "_id": 1},
    ).batch_size(5).max_time_ms(900000)

    embeddings = []
    chunk_ids = []
    count = 0
    for doc in cursor:
        emb = doc.get("embedding")
        if not emb or not isinstance(emb, list):
            continue
        if len(emb) != EMBEDDING_DIM:
            continue
        embeddings.append(emb)
        chunk_ids.append(str(doc.get("chunk_id") or doc["_id"]))
        count += 1
        if count % 200 == 0:
            log.info(f"  ... {count} embeddings")

    embeddings_arr = np.array(embeddings, dtype=np.float32)
    log.info(f"Terhequr {len(chunk_ids)} embeddings, shape={embeddings_arr.shape}")

    np.savez_compressed(CACHE_EMB, embeddings=embeddings_arr, chunk_ids=np.array(chunk_ids))
    log.info(f"Cache ruajtur: {CACHE_EMB}")
    return embeddings_arr, chunk_ids


def _run_kmeans(embeddings):
    from sklearn.cluster import KMeans
    log.info(f"Duke ekzekutuar K-means me k={K}...")
    t0 = time.time()
    km = KMeans(n_clusters=K, n_init=10, random_state=RANDOM_STATE, verbose=0)
    labels = km.fit_predict(embeddings)
    elapsed = round(time.time() - t0, 1)
    log.info(f"K-means perfundoi ne {elapsed}s")
    return km, labels


def main():
    if os.path.exists(ASSIGNMENTS_FILE):
        log.info(f"{ASSIGNMENTS_FILE} ekziston - faza 1 tashme e kryer.")
        return

    client, db = _get_dedicated_db()

    try:
        embeddings, chunk_ids = _fetch_embeddings(db)
        km, labels = _run_kmeans(embeddings)

        log.info("Duke llogaritur distancat per confidence...")
        distances = km.transform(embeddings).min(axis=1)

        log.info(f"Duke ruajtur {ASSIGNMENTS_FILE}...")
        assignments = {}
        for i, chunk_id in enumerate(chunk_ids):
            assignments[chunk_id] = {
                "topic_id": int(labels[i]),
                "distance": float(distances[i]),
            }
        with open(ASSIGNMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(assignments, f)

        np.savez_compressed(CENTROIDS_FILE, centroids=km.cluster_centers_, labels=labels)

        print()
        print("=" * 70)
        print("STATISTIKA E CLUSTER-EVE")
        print("=" * 70)
        for tid in range(K):
            mask = (labels == tid)
            count = int(mask.sum())
            if count == 0:
                print(f"  Topic {tid:2d}: 0 (bosh)")
                continue
            avg_dist = float(distances[mask].mean())
            print(f"  Topic {tid:2d}: {count:4d} dokumente, avg_dist={avg_dist:.3f}")

        print()
        print(f"Faza 1 perfundoi. Output: {ASSIGNMENTS_FILE}")
        print(f"Hapi tjeter: python _cluster_phase2.py")
    finally:
        client.close()


if __name__ == "__main__":
    main()