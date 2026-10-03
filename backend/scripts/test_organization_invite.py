# FILE: backend/scripts/test_organization_invite.py
"""Test: A funksionon ftesa e organizatës (limit + ACTIVE auto)?"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from bson import ObjectId
from app.core.db import get_db_instance
from app.core.security import get_password_hash


async def main():
    db = get_db_instance()

    # Pastro user-a test nëse ekzistojnë
    test_owner = "test_org_owner_xyz"
    test_invitee = "test_org_invitee_xyz@example.com"
    db.users.delete_many({"username": {"$in": [test_owner, "invited_xyz"]}})
    db.users.delete_many({"email": test_invitee})

    # 1. Krijo owner ACTIVE me TEAM_PLAN
    owner_id = db.users.insert_one({
        "username": test_owner,
        "email": "test_org_owner_xyz@example.com",
        "full_name": "Test Owner",
        "hashed_password": get_password_hash("TestPass123!@#"),
        "role": "STANDARD",
        "account_type": "ORGANIZATION",
        "product_plan": "TEAM_PLAN",
        "subscription_status": "ACTIVE",
        "subscription_expiry": None,
        "org_role": "OWNER",
        "consent_to_process": True,
        "is_deleted": False,
    }).inserted_id
    print(f"✅ Owner krijuar: {owner_id} (TEAM_PLAN, ACTIVE)")
    print()

    try:
        async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
            # 2. Login owner
            r = await client.post("/api/v1/auth/login", json={
                "username": test_owner,
                "password": "TestPass123!@#",
            })
            if r.status_code != 200:
                print(f"❌ Login dështoi: {r.status_code} — {r.text}")
                return
            token = r.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            print("✅ Login owner OK")
            print()

            # 3. Shiko organizatën
            r = await client.get("/api/v1/organizations/me", headers=headers)
            print(f"3. GET /organizations/me → {r.status_code}")
            if r.status_code == 200:
                org = r.json()
                print(f"   Plan: {org.get('plan_tier')}, Limit: {org.get('user_limit')}, Aktiv: {org.get('current_active_users')}")
            print()

            # 4. Fto user
            r = await client.post("/api/v1/organizations/invite",
                                   headers=headers,
                                   json={"email": test_invitee})
            print(f"4. POST /organizations/invite → {r.status_code}")
            if r.status_code != 200:
                print(f"   ERROR: {r.text}")
            else:
                print(f"   ✅ {r.json()}")
            print()

            # 5. Kontrollo DB
            invited = db.users.find_one({"email": test_invitee})
            if invited:
                print(f"5. I ftuari në DB:")
                print(f"   status: {invited.get('status')}")
                print(f"   subscription_status: {invited.get('subscription_status')}")
                print(f"   organization_id: {invited.get('organization_id')}")
                print(f"   invitation_token: {'✅ ka token' if invited.get('invitation_token') else '❌ mungon'}")
            else:
                print(f"5. ❌ I ftuari NUK u gjet në DB")
            print()

            # 6. Provo të ftosh me limit 1 (nëse owner është SOLO në vend të TEAM)
            # Kjo është vetëm për test — kur owner është TEAM, limit është 5
            print("─" * 70)
            print("PËRMBLEDHJE:")
            print("─" * 70)
            print(f"  Owner ACTIVE → fton: {'✅' if r.status_code == 200 else '❌'}")
            print(f"  I ftuari ka ACTIVE:  {'✅' if invited and invited.get('subscription_status') == 'ACTIVE' else '❌'}")
            print(f"  I ftuari ka token:   {'✅' if invited and invited.get('invitation_token') else '❌'}")
            print(f"  I ftuari ka org_id:  {'✅' if invited and invited.get('organization_id') else '❌'}")

    finally:
        # Pastro
        db.users.delete_one({"_id": owner_id})
        db.users.delete_many({"email": test_invitee})
        db.organizations.delete_one({"_id": owner_id})
        print(f"\n🧹 Test u pastrua.")


if __name__ == "__main__":
    asyncio.run(main())