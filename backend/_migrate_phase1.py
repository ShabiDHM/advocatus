# -*- coding: utf-8 -*-
"""
FAZA 1 — Migrimi i organizatës (V1.1).

KRYEN:
  1. Fshin te gjitha case-t (test)
  2. Fshin dokumentet e case-ve + vectors + extractions + chat history
  3. Fshin organizatat dublikate (2 "Zyra Ligjore")
  4. Perditeson ADMIN: organization_role=OWNER, org_access_level=FULL
  5. Perditeson STANDARD: organization_role=MEMBER, org_access_level=FULL
  6. Perditeson organizaten "Shaban Bala": shton billing, settings, created_at

MBRON (nuk fshihen):
  - legal_knowledge_base (global knowledge: statute + caselaw)
  - users
  - organizations (vetem dublikatat fshihen)

Ekzekutim:
  python _migrate_phase1.py           # Dry-run
  python _migrate_phase1.py --apply   # Apliko
"""
import sys
from datetime import datetime, timezone
from bson import ObjectId
from app.core.db import get_db

APPLY = "--apply" in sys.argv

db = get_db()

# ═══════════════════════════════════════════════════════════════════════════
# KONFIGURIMI
# ═══════════════════════════════════════════════════════════════════════════

ORG_KEEP_ID = ObjectId("6a79133349ee7ee103bbeefa")
ORG_DELETE_IDS = [
    ObjectId("6a590293c2808c18abb3bf72"),
    ObjectId("6a69f52fc957567594ee4947"),
]

ADMIN_USER_ID = ObjectId("6a79133349ee7ee103bbeefa")
STANDARD_USER_ID = ObjectId("6a8e129c02d1fd46ca5ab3a4")

# Koleksionet qe lidhen me case (test) — TE FSHIHEN
# ⚠️ NUK përfshihet 'legal_knowledge_base' (global knowledge)!
CASE_RELATED_COLLECTIONS = [
    "cases",
    "documents",                  # V1.1: I RI — dokumentet e case-ve
    "case_extractions",
    "case_synthesis",
    "case_chat_history",
    "case_cross_references",
    "case_graphs",
    "legal_analysis_cache",
    "archives",
    "expenses",
    "invoices",
    "calendar_events",
    "media_evidence",
    "chat_feedback",
    "user_vectors",
    "case_orders",
]

# ═══════════════════════════════════════════════════════════════════════════
# DIAGNOSTIKIM
# ═══════════════════════════════════════════════════════════════════════════

print("=" * 70)
print("FAZA 1 — MIGRIMI I ORGANIZATES (V1.1)")
print("=" * 70)
print(f"Modi: {'APPLY' if APPLY else 'DRY-RUN'}")
print()

print("─" * 70)
print("0. MBROJTJA E GLOBAL KNOWLEDGE BASE (kontroll)")
print("─" * 70)
kb = db["legal_knowledge_base"]
kb_total = kb.count_documents({})
kb_statute = kb.count_documents({"category": "statute"})
kb_caselaw = kb.count_documents({"category": "caselaw"})
kb_academic = kb.count_documents({"category": "academic"})
print(f"  legal_knowledge_base: {kb_total} docs")
print(f"    statute:  {kb_statute}")
print(f"    caselaw:  {kb_caselaw}")
print(f"    academic: {kb_academic}")
print(f"  KY KOLEKSION NUK DO TE PREKET")
print()

print("─" * 70)
print("1. KOLEKSIONET E PREKURA (numri i dokumenteve)")
print("─" * 70)

totals = {}
for coll_name in CASE_RELATED_COLLECTIONS:
    try:
        count = db[coll_name].count_documents({})
        totals[coll_name] = count
        if count > 0:
            print(f"  {coll_name:<30} {count:>6} docs")
    except Exception as e:
        print(f"  {coll_name:<30} (gabim: {e})")

total_docs = sum(totals.values())
print(f"  {'─' * 30} {'─' * 6}")
print(f"  TOTAL: {total_docs} docs qe do fshihen")
print()

print("─" * 70)
print("2. ORGANIZATAT")
print("─" * 70)
print(f"  MBETET:  {ORG_KEEP_ID}  'Shaban Bala'")
for oid in ORG_DELETE_IDS:
    org = db.organizations.find_one({"_id": oid})
    print(f"  FSHIHET: {oid}  '{org.get('name') if org else '?'}'")
print()

print("─" * 70)
print("3. PËRDITËSIMET E USERAVE")
print("─" * 70)

admin = db.users.find_one({"_id": ADMIN_USER_ID})
standard = db.users.find_one({"_id": STANDARD_USER_ID})

print("ADMIN (shabanbala@gmail.com):")
if admin:
    print(f"  organization_id:   {admin.get('organization_id')} -> {ORG_KEEP_ID}")
    print(f"  organization_role: {admin.get('organization_role')} -> OWNER")
    print(f"  org_access_level:  {admin.get('org_access_level')} -> FULL")
else:
    print("  NUK GJENDET")

print()
print("STANDARD (shabanbala@live.com):")
if standard:
    print(f"  organization_id:   {standard.get('organization_id')} -> {ORG_KEEP_ID}")
    print(f"  organization_role: {standard.get('organization_role')} -> MEMBER")
    print(f"  org_access_level:  {standard.get('org_access_level')} -> FULL")
else:
    print("  NUK GJENDET")

print()

print("─" * 70)
print("4. PËRDITËSIMI I ORGANIZATËS")
print("─" * 70)
org = db.organizations.find_one({"_id": ORG_KEEP_ID})
if org:
    print(f"  _id:        {ORG_KEEP_ID}")
    print(f"  name:       {org.get('name')} (nuk ndryshon)")
    print(f"  owner_id:   {org.get('owner_id')} -> {ADMIN_USER_ID}")
    print(f"  member_ids: {org.get('member_ids')} -> [{ADMIN_USER_ID}, {STANDARD_USER_ID}]")
    print(f"  + shtohen:  created_at, updated_at, billing, settings")
else:
    print("  NUK GJENDET")

print()
print("=" * 70)

# ═══════════════════════════════════════════════════════════════════════════
# APPLY
# ═══════════════════════════════════════════════════════════════════════════

if not APPLY:
    print("DRY-RUN. Per te aplikuar: python _migrate_phase1.py --apply")
    print("=" * 70)
    sys.exit(0)

print("APLIKIMI")
print("=" * 70)

confirm = input("\nKonfirmo? (po/jo): ").strip().lower()
if confirm not in ("po", "p", "yes", "y"):
    print("Anulo.")
    sys.exit(0)

now = datetime.now(timezone.utc)

# 1. Fshij case-t + dokumentet + related
print("\n[1/6] Duke fshire case-t + dokumentet + related...")
deleted_total = 0
for coll_name in CASE_RELATED_COLLECTIONS:
    try:
        result = db[coll_name].delete_many({})
        if result.deleted_count > 0:
            print(f"  OK {coll_name}: {result.deleted_count} docs")
            deleted_total += result.deleted_count
    except Exception as e:
        print(f"  WARN {coll_name}: {e}")

print(f"  TOTAL: {deleted_total} docs")

# 2. Fshij organizatat dublikate
print("\n[2/6] Duke fshire organizatat dublikate...")
for oid in ORG_DELETE_IDS:
    result = db.organizations.delete_one({"_id": oid})
    print(f"  OK {oid}: deleted={result.deleted_count}")

# 3. Perditeso ADMIN
print("\n[3/6] Duke perditesuar ADMIN...")
result = db.users.update_one(
    {"_id": ADMIN_USER_ID},
    {"$set": {
        "organization_id": ORG_KEEP_ID,
        "organization_role": "OWNER",
        "org_access_level": "FULL",
    }}
)
print(f"  OK Modified: {result.modified_count}")

# 4. Perditeso STANDARD
print("\n[4/6] Duke perditesuar STANDARD...")
result = db.users.update_one(
    {"_id": STANDARD_USER_ID},
    {"$set": {
        "organization_id": ORG_KEEP_ID,
        "organization_role": "MEMBER",
        "org_access_level": "FULL",
    }}
)
print(f"  OK Modified: {result.modified_count}")

# 5. Perditeso organizaten
print("\n[5/6] Duke perditesuar organizaten...")
result = db.organizations.update_one(
    {"_id": ORG_KEEP_ID},
    {
        "$set": {
            "owner_id": ADMIN_USER_ID,
            "member_ids": [ADMIN_USER_ID, STANDARD_USER_ID],
            "updated_at": now,
            "billing": {
                "plan": "TEAM_PLAN",
                "max_members": 5,
                "status": "active",
            },
            "settings": {
                "invite_expiry_days": 7,
            },
        },
        "$setOnInsert": {
            "created_at": now,
        },
    },
    upsert=True,
)
print(f"  OK Modified: {result.modified_count}, Upserted: {result.upserted_id}")

# 6. Verifikim
print("\n[6/6] VERIFIKIM")
print("─" * 70)

admin_after = db.users.find_one({"_id": ADMIN_USER_ID}, {"email": 1, "role": 1, "organization_id": 1, "organization_role": 1, "org_access_level": 1})
standard_after = db.users.find_one({"_id": STANDARD_USER_ID}, {"email": 1, "role": 1, "organization_id": 1, "organization_role": 1, "org_access_level": 1})
org_after = db.organizations.find_one({"_id": ORG_KEEP_ID})

print(f"\nADMIN: {admin_after.get('email')}")
print(f"  role:              {admin_after.get('role')}")
print(f"  organization_id:   {admin_after.get('organization_id')}")
print(f"  organization_role: {admin_after.get('organization_role')}")
print(f"  org_access_level:  {admin_after.get('org_access_level')}")

print(f"\nSTANDARD: {standard_after.get('email')}")
print(f"  role:              {standard_after.get('role')}")
print(f"  organization_id:   {standard_after.get('organization_id')}")
print(f"  organization_role: {standard_after.get('organization_role')}")
print(f"  org_access_level:  {standard_after.get('org_access_level')}")

print(f"\nORGANIZATA: {org_after.get('name')}")
print(f"  _id:         {org_after.get('_id')}")
print(f"  owner_id:    {org_after.get('owner_id')}")
print(f"  member_ids:  {org_after.get('member_ids')}")

kb_after = db["legal_knowledge_base"].count_documents({})
print()
print("─" * 70)
print("VERIFIKIM I GLOBAL KNOWLEDGE BASE")
print("─" * 70)
print(f"  PARA:   {kb_total} docs")
print(f"  PAS:    {kb_after} docs")
if kb_after == kb_total:
    print(f"  OK E PAPREKUR - sakte!")
else:
    print(f"  KUJDES: NDRYSHIM! Kontrollo menjehere!")

remaining_orgs = db.organizations.count_documents({})
cases_remaining = db.cases.count_documents({})
print()
print(f"  Organizata total: {remaining_orgs} (duhet 1)")
print(f"  Case total:       {cases_remaining} (duhet 0)")

print()
print("=" * 70)
print("FAZA 1 PERFUNDOI")
print("=" * 70)