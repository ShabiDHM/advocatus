# FILE: backend/scripts/test_active_access.py
"""Test: user me subscription_status='ACTIVE' duhet të kalojë në të gjitha endpoint-et."""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from app.core.db import get_db_instance
from app.core.security import get_password_hash


TEST_USERNAME = "test_active_user_xyz"
TEST_EMAIL = "test_active_xyz@example.com"
TEST_PASSWORD = "TestPass123!@#"


async def main():
    db = get_db_instance()
    db.users.delete_many({"username": TEST_USERNAME})

    result = db.users.insert_one({
        "username": TEST_USERNAME,
        "email": TEST_EMAIL,
        "full_name": "Test Active",
        "hashed_password": get_password_hash(TEST_PASSWORD),
        "role": "STANDARD",
        "account_type": "SOLO",
        "subscription_tier": "PRO",
        "product_plan": "SOLO_PLAN",
        "subscription_status": "ACTIVE",
        "subscription_expiry": None,
        "consent_to_process": True,
        "is_deleted": False,
    })
    user_id = result.inserted_id
    print(f"✅ User test ACTIVE u krijua: {user_id}")
    print()

    try:
        async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
            r = await client.post("/api/v1/auth/login", json={
                "username": TEST_USERNAME,
                "password": TEST_PASSWORD,
            })
            print(f"1. POST /auth/login → {r.status_code}")
            if r.status_code != 200:
                print(f"   ERROR: {r.text}")
                return
            token = r.json().get("access_token")
            print(f"   ✅ Token i marrë")
            print()

            headers = {"Authorization": f"Bearer {token}"}

            tests = [
                ("GET", "/api/v1/cases"),
                ("GET", "/api/v1/calendar/events"),
                ("GET", "/api/v1/finance/invoices"),
                ("GET", "/api/v1/finance/expenses"),
                ("GET", "/api/v1/archive/items"),
                ("GET", "/api/v1/users/me"),
            ]

            print("─" * 70)
            print(f"{'Endpoint':<40} {'Status':<10} {'Rezultat'}")
            print("─" * 70)

            broken = []
            working = []

            for method, path in tests:
                try:
                    r = await client.request(method, path, headers=headers)
                    status = r.status_code
                    if status == 200:
                        result = "✅ Punon"
                        working.append(path)
                    elif status in (401, 403, 402):
                        result = "🔴 BLLOKUAR — duhet të kalojë"
                        broken.append(path)
                    else:
                        result = f"⚠️  {status}"
                    print(f"{path:<40} {status:<10} {result}")
                except Exception as e:
                    print(f"{path:<40} ERROR: {e}")

            print("─" * 70)
            print()
            print(f"📊 REZULTATI:")
            print(f"   Punojnë (200):   {len(working)}")
            print(f"   Të thyera:       {len(broken)}")
            print()

            if broken:
                print("🔴 REGRESIONE — useri me abonim aktiv duhet të kalojë:")
                for p in broken:
                    print(f"   - {p}")
            else:
                print("✅ NUK KA REGRESIONE — useri aktiv ka qasje të plotë")

    finally:
        db.users.delete_one({"_id": user_id})
        print(f"\n🧹 User test u fshi.")


if __name__ == "__main__":
    asyncio.run(main())