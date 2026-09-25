# FILE: backend/test_verify_draft.py
# PHOENIX PROTOCOL - DIAGNOSTIC V1.2
# V1.2: _probe_extraction_len lexon documents.content (ku DraftVerifier lexon realisht).
#       - documents: {_id, owner_id, case_id (ObjectId), file_name, storage_key,
#                     mime_type, page_count, status, content, extracted_text, text, ...}
#       - case_extractions: NUK ruan tekstin (vetëm NER + metadata)
#
# Përdorimi (nga backend/):
#   python test_verify_draft.py
#   python test_verify_draft.py <case_id> <doc_id> [doc_type]

import sys
import os
import time
import logging

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
for noisy in ("urllib3", "httpx", "httpcore", "openai", "pymongo", "redis"):
    logging.getLogger(noisy).setLevel(logging.ERROR)


def _sep(c="=", n=78):
    print(c * n)


def _fmt(sec):
    return f"{sec:.2f}s"


# ═══════════════════════════════════════════════════════════════════════════
# DB HELPERS — strukturë reale
# ═══════════════════════════════════════════════════════════════════════════

def _find_docs_for_case(db, case_id):
    """
    Kthen dokumentet e një case nga koleksioni 'documents'.
    case_id në 'documents' është ObjectId.
    """
    from bson import ObjectId
    try:
        c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
    except Exception:
        c_oid = case_id

    docs = []
    try:
        cursor = db["documents"].find(
            {"$or": [{"case_id": c_oid}, {"case_id": case_id}]}
        )
        docs = list(cursor)
    except Exception as e:
        print(f"⚠️ _find_docs_for_case error: {e}")
    return docs


def _doc_id(d):
    return str(d.get("_id") or d.get("id") or d.get("document_id") or "")


def _doc_name(d):
    return (
        d.get("file_name")
        or d.get("filename")
        or d.get("name")
        or d.get("original_name")
        or "(pa emër)"
    )


def _probe_extraction_len(db, case_id, doc_id):
    """
    V1.2: Kontrollon documents.content (ku DraftVerifier lexon realisht).
    case_extractions NUK ruan tekstin — vetëm NER + metadata.
    """
    from bson import ObjectId
    try:
        d_oid = ObjectId(doc_id) if ObjectId.is_valid(doc_id) else doc_id
        c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id

        doc = db["documents"].find_one({
            "_id": d_oid,
            "$or": [
                {"case_id": c_oid},
                {"case_id": case_id},
                {"case_id": str(c_oid)},
            ],
        })
        if not doc:
            return 0

        text = (
            doc.get("content")
            or doc.get("extracted_text")
            or doc.get("text")
            or ""
        )
        return len(text) if isinstance(text, str) else 0
    except Exception as e:
        print(f"⚠️ _probe_extraction_len error: {e}")
        return 0


def _pick_case(db):
    """Liston case-t dhe kthen (case_id, docs) për case-in e parë me docs."""
    _sep("─")
    print("📁 CASE-T NË DB:")
    _sep("─")

    cases = list(db.cases.find({}, {"_id": 1, "title": 1, "name": 1}).limit(30))
    if not cases:
        print("   (asnjë case)")
        return None, []

    enriched = []
    for c in cases:
        cid = str(c["_id"])
        title = c.get("title") or c.get("name") or "(pa titull)"
        docs = _find_docs_for_case(db, cid)
        enriched.append((cid, title, docs))

    for i, (cid, title, docs) in enumerate(enriched, 1):
        print(f"  {i:2d}. {cid}  |  docs={len(docs):2d}  |  {title[:50]}")

    for cid, title, docs in enriched:
        if docs:
            print(f"\n🔎 Auto-pick: {cid} ({title[:55]})")
            return cid, docs
    return None, []


def _pick_doc(db, case_id, docs):
    """Liston dokumentet, kthen doc_id me tekst më të gjatë."""
    _sep("─")
    print(f"📄 DOKUMENTET NË CASE {case_id} ({len(docs)}):")
    _sep("─")

    best_id = None
    best_len = 0
    for i, d in enumerate(docs, 1):
        did = _doc_id(d)
        name = _doc_name(d)
        chars = _probe_extraction_len(db, case_id, did)
        flag = "✓" if chars >= 500 else " "
        print(f"  {flag} {i:2d}. {did}  |  {chars if chars >= 0 else '?':>7} chars  |  {name[:45]}")
        if chars > best_len:
            best_len = chars
            best_id = did

    return best_id, best_len


def _check_persisted(db, case_id, doc_id):
    """Kontrollon case_document_verifications.{doc_id} në cases."""
    from bson import ObjectId
    try:
        c_oid = ObjectId(case_id) if ObjectId.is_valid(case_id) else case_id
    except Exception:
        c_oid = case_id
    case = db.cases.find_one(
        {"_id": c_oid},
        {"case_document_verifications": 1},
    )
    if not case:
        return None
    verifs = case.get("case_document_verifications") or {}
    return verifs.get(doc_id)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    _sep()
    print("TEST DIAGNOSTIKUES — DraftVerifier.verify() v1.2")
    print("PHOENIX PROTOCOL — Verifiko Draftin")
    _sep()

    try:
        from app.core.db import get_db
        db = get_db()
    except Exception as e:
        print(f"❌ Import/MongoDB error: {e}")
        sys.exit(1)

    if db is None:
        print("❌ get_db() ktheu None.")
        sys.exit(1)

    print("✓ Lidhja me MongoDB OK.\n")

    args = sys.argv[1:]
    case_id = args[0] if len(args) > 0 else None
    doc_id = args[1] if len(args) > 1 else None
    doc_type = args[2] if len(args) > 2 else "kallzim_penal"

    try:
        from app.services.document_review.verify_prompts import VERIFY_DOC_TYPES
    except Exception as e:
        print(f"❌ Import verify_prompts failed: {e}")
        sys.exit(1)

    if doc_type not in VERIFY_DOC_TYPES:
        print(f"❌ doc_type i panjohur: '{doc_type}'")
        print(f"   Të lejuara: {sorted(VERIFY_DOC_TYPES.keys())}")
        sys.exit(1)

    print(f"📌 doc_type: {doc_type} → {VERIFY_DOC_TYPES[doc_type]}")

    if not case_id:
        case_id, docs = _pick_case(db)
        if not case_id:
            print("\n❌ Asnjë case me dokumente. Ndal.")
            sys.exit(1)
    else:
        docs = _find_docs_for_case(db, case_id)
        if not docs:
            print(f"\n❌ Case nuk ka dokumente: {case_id}")
            sys.exit(1)

    if not doc_id:
        doc_id, best_len = _pick_doc(db, case_id, docs)
        if not doc_id or best_len < 100:
            print(f"\n❌ Nuk u gjet draft me tekst (best={best_len} chars).")
            sys.exit(1)
        print(f"\n🔎 Zgjedhur: {doc_id} ({best_len} chars)")

    _sep()
    print(f"🚀 EKZEKUTIM: case={case_id}")
    print(f"            doc={doc_id}")
    print(f"            doc_type={doc_type}")
    _sep()
    print()

    def progress(event, payload):
        ts = time.strftime("%H:%M:%S")
        if event == "step_started":
            print(f"[{ts}] ⏳ STEP:      {payload.get('step_title', '?')}")
        elif event == "section_started":
            print(f"[{ts}] ▶️  SECTION:   {payload.get('section_title', '?')}")
        elif event == "section_completed":
            key = payload.get("section_key", "?")
            n = payload.get("content_length", 0)
            print(f"[{ts}] ✅ DONE:      {key} ({n} chars)")

    try:
        from app.services.document_review.draft_verifier import get_draft_verifier
        verifier = get_draft_verifier(db)
    except Exception as e:
        print(f"❌ Import DraftVerifier failed: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)

    t0 = time.time()
    try:
        result = verifier.verify(
            case_id=case_id,
            document_id=doc_id,
            doc_type=doc_type,
            user_id="diagnostic",
            progress_callback=progress,
            section_stream_callback=None,
        )
    except Exception as e:
        print(f"\n❌ Verifier crashed: {type(e).__name__}: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
    total = time.time() - t0

    print()
    _sep()
    print("📊 REZULTATI")
    _sep()

    print(f"Status:              {result.get('status')}")
    print(f"Readiness:           {result.get('readiness')}")
    print(f"File:                {result.get('file_name')}")
    print(f"Doc type label:      {result.get('doc_type_label')}")
    print(f"Duration (total):    {_fmt(total)}")
    print(f"Persisted:           {result.get('persisted', False)}")

    stats = result.get("stats", {}) or {}
    print()
    print(f"Sections generated:  {stats.get('sections_generated')}/{stats.get('sections_total')}")
    print(f"Articles verified:   {stats.get('articles_verified')}/{stats.get('articles_total')}")
    print(f"Precedents found:    {stats.get('precedents_found')}")
    print(f"Report chars:        {stats.get('report_chars')}")
    print(f"Execution mode:      {stats.get('execution_mode')}")
    print(f"Sections total sec:  {stats.get('sections_total_sec')}")
    print(f"Text length:         {stats.get('text_length')}")

    print()
    _sep("─")
    print("⏱️  PER-SECTION TIMING:")
    _sep("─")
    for k, s in (result.get("section_stats") or {}).items():
        dur = s.get("duration_sec", "?")
        ln = s.get("content_length", 0)
        ctx = s.get("context_chars", "?")
        err = s.get("error")
        tag = "❌" if err else "✅"
        print(f"  {tag} {k:24s}  {str(dur):>7}s  |  ctx={ctx}  out={ln}")
        if err:
            print(f"      ERROR: {str(err)[:140]}")

    print()
    _sep("─")
    print("💾 PERSIST CHECK (case_document_verifications):")
    _sep("─")
    persisted = _check_persisted(db, case_id, doc_id)
    if not persisted:
        print("  ⚠️  NUK u gjet në DB.")
    else:
        print(f"  ✓ u gjet: built_at={persisted.get('built_at')}")
        print(f"            readiness={persisted.get('readiness')}")
        print(f"            doc_type={persisted.get('doc_type')}")
        print(f"            report_chars={len(persisted.get('full_report') or '')}")

    if result.get("error_message"):
        print()
        print(f"❌ ERROR MESSAGE: {result['error_message']}")

    full = result.get("full_report") or ""
    print()
    _sep("─")
    print(f"📄 FULL REPORT ({len(full)} chars) — 80 rreshtat e parë:")
    _sep("─")
    for line in full.splitlines()[:80]:
        print(line)
    _sep("─")

    print()
    _sep()
    print(f"✅ Test përfundoi. Koha totale: {_fmt(total)}")
    _sep()

    sys.exit(0 if result.get("status") == "completed" else 2)


if __name__ == "__main__":
    main()