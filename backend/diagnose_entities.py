# FILE: backend/diagnose_entities.py
# Shfaq të gjitha entitetet nga ekstraktimi më i fundit i ruajtur.

from app.core.db import get_db_instance


def main():
    db = get_db_instance()
    print(f"✅ DB: {db.name}\n")

    # Gjej ekstraktimin më të fundit
    latest = db["case_extractions"].find_one(
        {},
        sort=[("completed_at", -1)]
    )

    if not latest:
        print("❌ Nuk ka ekstraktime në case_extractions.")
        return

    print("=" * 70)
    print("📄 EKSTRAKTIMI MË I FUNDIT:")
    print("=" * 70)
    print(f"   document_id:    {latest.get('document_id')}")
    print(f"   file_name:      {latest.get('file_name')}")
    print(f"   document_type:  {latest.get('document_type')}")
    print(f"   text_length:    {latest.get('text_length'):,}")
    print(f"   completed_at:   {latest.get('completed_at')}")

    stats = latest.get("stats", {})
    print(f"\n   stats:")
    for k, v in stats.items():
        print(f"      {k}: {v}")

    ner_stats = latest.get("ner_stats", {})
    print(f"\n   ner_stats:")
    for k, v in ner_stats.items():
        print(f"      {k}: {v}")

    # Të gjitha entitetet sipas tipit
    print("\n" + "=" * 70)
    print("🏷️  ENTITETET SIPAS TIPIT:")
    print("=" * 70)

    entities_by_type = latest.get("entities_by_type", {})
    for label in sorted(entities_by_type.keys()):
        items = entities_by_type[label]
        if not items:
            continue
        print(f"\n[{label}] — {len(items)} entitete:")
        for e in items:
            text = e.get("text", "?")
            orig = e.get("original_text", "")
            conf = e.get("confidence", "?")
            extra = ""
            if orig and orig != text:
                extra = f" (orig: '{orig}')"
            if "role_conflict_resolved" in e:
                extra += f" [CONFLICT: {e['role_conflict_resolved']} → {e['role_conflict_winner']}]"
            print(f"   - '{text}' (conf={conf}){extra}")

    # Analizë specifike për problemet e njohura
    print("\n" + "=" * 70)
    print("🔍 ANALIZË E PROBLEMEVE SPECIFIKE:")
    print("=" * 70)

    entities_flat = latest.get("entities_flat", [])

    # 1. Emrat që përmbajnë titull
    titles = ["Gjyqtari", "Gjyqtarja", "Prokurori", "Prokuroresha",
              "Avokati", "Avokatja", "Kryetari", "Kryesuesi",
              "Dr.", "Prof.", "Z.", "Znj."]
    with_title = [
        e for e in entities_flat
        if any(t in e.get("text", "") for t in titles)
    ]
    print(f"\n1️⃣  Entitete që ende përmbajnë titull: {len(with_title)}")
    for e in with_title:
        print(f"   - [{e.get('label')}] '{e.get('text')}'")

    # 2. Bekim Dugolli në role të ndryshme
    print(f"\n2️⃣  Emrat që shfaqen në role të ndryshme:")
    by_text = {}
    for e in entities_flat:
        key = e.get("text", "").lower().strip()
        by_text.setdefault(key, []).append(e)

    multi_role_found = False
    for text_key, group in by_text.items():
        labels = set(g.get("label") for g in group)
        if len(labels) > 1:
            multi_role_found = True
            print(f"\n   '{text_key}':")
            for g in group:
                print(f"      [{g.get('label')}] '{g.get('text')}' "
                      f"(conf={g.get('confidence')})")
    if not multi_role_found:
        print("   ✅ Asnjë emër në role të ndryshme")

    # 3. PROSECUTOR-t
    print(f"\n3️⃣  Të gjithë PROSECUTOR:")
    for e in entities_by_type.get("PROSECUTOR", []):
        print(f"   - '{e.get('text')}' (conf={e.get('confidence')})")
        ctx = e.get("context", "")[:120]
        print(f"     ctx: {ctx}")

    # 4. Emrat me casing të ndryshëm
    print(f"\n4️⃣  Emra me casing të ndryshëm (duplikat i mundshëm):")
    by_lower = {}
    for e in entities_flat:
        key = e.get("text", "").lower().strip()
        by_lower.setdefault(key, []).append(e)

    casing_issue = False
    for key, group in by_lower.items():
        if len(group) > 1:
            texts = set(g.get("text") for g in group)
            if len(texts) > 1:
                casing_issue = True
                print(f"\n   lowercase='{key}':")
                for g in group:
                    print(f"      [{g.get('label')}] '{g.get('text')}'")

    if not casing_issue:
        print("   ✅ Asnjë duplikat casing")

    print("\n" + "=" * 70)
    print("🏁 FUNDI I DIAGNOZËS")
    print("=" * 70)


if __name__ == "__main__":
    main()