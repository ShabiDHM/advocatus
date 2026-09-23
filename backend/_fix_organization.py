# -*- coding: utf-8 -*-
"""
Diagnostikon dhe rregullon strukturën e organizatës.

Faza 1 (default): Vetem diagnostikim + propozim (nuk ndryshon gje)
Faza 2 (--apply): Aplikon ndryshimet me konfirmim

Ekzekutim:
  python _fix_organization.py           # Vetem shfaq
  python _fix_organization.py --apply   # Aplikon
"""
import sys
from bson import ObjectId
from app.core.db import get_db

APPLY = "--apply" in sys.argv

db = get_db()

# ═══════════════════════════════════════════════════════════════════════════
# GJENDJA AKTUALE
# ═══════════════════════════════════════════════════════════════════════════
print("=" * 70)
print("GJENDJA AKTUALE")
print("=" * 70)

print("\nUSERAT:")
users = list(db["users"].find(
    {},
    {"email": 1, "username": 1, "role": 1,
     "organization_id": 1, "organization_role": 1, "org_access_level": 1}
).limit(30))
user_by_email = {}
for u in users:
    user_by_email[u["email"]] = u
    print(f"  {u['email']}")
    print(f"    _id:               {u['_id']}")
    print(f"    username:          {u.get('username')}")
    print(f"    role:              {u.get('role')}")
    print(f"    organization_id:   {u.get('organization_id')}")
    print(f"    organization_role: {u.get('organization_role')}")
    print(f"    org_access_level:  {u.get('org_access_level')}")
    print()

print("\nORGANIZATAT:")
orgs = list(db["organizations"].find({}).limit(20))
for o in orgs:
    print(f"  {o['_id']}")
    print(f"    name:       {o.get('name')}")
    print(f"    owner_id:   {o.get('owner_id')}")
    print(f"    member_ids: {o.get('member_ids')}")
    print()

print("\nLENDA:")
cases = list(db["cases"].find({}, {
    "title": 1, "owner_id": 1, "user_id": 1, "organization_id": 1,
    "assigned_user_ids": 1
}).limit(10))
for c in cases:
    print(f"  {c['_id']}")
    print(f"    title:             {c.get('title')}")
    print(f"    owner_id:          {c.get('owner_id')}")
    print(f"    user_id:           {c.get('user_id')}")
    print(f"    organization_id:   {c.get('organization_id')}")
    print(f"    assigned_user_ids: {c.get('assigned_user_ids')}")
    print()

# ═══════════════════════════════════════════════════════════════════════════
# PROPOZIMI
# ═══════════════════════════════════════════════════════════════════════════
print("=" * 70)
print("PROPOZIMI")
print("=" * 70)

admin = user_by_email.get("shabanbala@gmail.com")
standard = user_by_email.get("shabanbala@live.com")

if not admin:
    print("❌ Nuk gjendet useri ADMIN (shabanbala@gmail.com)")
    sys.exit(1)

if not standard:
    print("⚠️  Nuk gjendet useri STANDARD (shabanbala@live.com)")
    print("   Do të rregullohet vetëm ADMIN.")

# Zgjidh organizaten: prefero "Shaban Bala" (already referenced), ose e para
target_org = None
for o in orgs:
    if o.get("name") == "Shaban Bala":
        target_org = o
        break
if not target_org and orgs:
    target_org = orgs[0]

if not target_org:
    print("❌ Nuk ka organizata në DB. Krijoje një me 'Create Organization' në UI.")
    sys.exit(1)

org_id = target_org["_id"]
admin_id = admin["_id"]
standard_id = standard["_id"] if standard else None

print(f"\nOrganizata target: '{target_org.get('name')}' ({org_id})")
print()
print("Ndryshimet e propozuara:")
print(f"  1. organizations._id={org_id}")
print(f"       owner_id:   {target_org.get('owner_id')} → {admin_id}")
print(f"       member_ids: {target_org.get('member_ids')} → [{admin_id}, {standard_id}]")
print()
print(f"  2. users._id={admin_id} (ADMIN)")
print(f"       organization_id:   {admin.get('organization_id')} → {org_id}")
print(f"       organization_role: {admin.get('organization_role')} → OWNER")
print()
if standard:
    print(f"  3. users._id={standard_id} (STANDARD)")
    print(f"       organization_id:   {standard.get('organization_id')} → {org_id}")
    print(f"       organization_role: {standard.get('organization_role')} → MEMBER")

print()
print("=" * 70)
if not APPLY:
    print("DRY-RUN. Për të aplikuar: python _fix_organization.py --apply")
    print("=" * 70)
    sys.exit(0)

print("APLIKIMI")
print("=" * 70)

# ═══════════════════════════════════════════════════════════════════════════
# APPLY
# ═══════════════════════════════════════════════════════════════════════════

confirm = input("\nKonfirmo aplikimin? (po/jo): ").strip().lower()
if confirm not in ("po", "p", "yes", "y"):
    print("Anulo.")
    sys.exit(0)

# 1. Update org
member_ids = [admin_id]
if standard_id:
    member_ids.append(standard_id)

org_result = db["organizations"].update_one(
    {"_id": org_id},
    {"$set": {
        "owner_id": admin_id,
        "member_ids": member_ids,
    }}
)
print(f"✅ organizations update: modified={org_result.modified_count}")

# 2. Update admin
admin_result = db["users"].update_one(
    {"_id": admin_id},
    {"$set": {
        "organization_id": org_id,
        "organization_role": "OWNER",
        "org_access_level": "FULL",
    }}
)
print(f"✅ users ADMIN update: modified={admin_result.modified_count}")

# 3. Update standard
if standard_id:
    std_result = db["users"].update_one(
        {"_id": standard_id},
        {"$set": {
            "organization_id": org_id,
            "organization_role": "MEMBER",
            "org_access_level": "FULL",
        }}
    )
    print(f"✅ users STANDARD update: modified={std_result.modified_count}")

print()
print("=" * 70)
print("VERIFIKIM")
print("=" * 70)

org_after = db["organizations"].find_one({"_id": org_id})
print(f"Organizata: {org_after.get('name')}")
print(f"  owner_id:   {org_after.get('owner_id')}")
print(f"  member_ids: {org_after.get('member_ids')}")
print()

admin_after = db["users"].find_one({"_id": admin_id}, {"email": 1, "role": 1, "organization_id": 1, "organization_role": 1})
print(f"ADMIN: {admin_after.get('email')}")
print(f"  role:              {admin_after.get('role')}")
print(f"  organization_id:   {admin_after.get('organization_id')}")
print(f"  organization_role: {admin_after.get('organization_role')}")
print()

if standard_id:
    std_after = db["users"].find_one({"_id": standard_id}, {"email": 1, "role": 1, "organization_id": 1, "organization_role": 1})
    print(f"STANDARD: {std_after.get('email')}")
    print(f"  role:              {std_after.get('role')}")
    print(f"  organization_id:   {std_after.get('organization_id')}")
    print(f"  organization_role: {std_after.get('organization_role')}")

print()
print("✅ PËRFUNDOI")