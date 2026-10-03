# FILE: backend/scripts/test_inactive_access.py
"""
Test: A mundet user me subscription_status='INACTIVE' të hyjë në endpoint-e?
Krijon user test, provon endpoint-e, pastaj fshin user-in.
"""
import os
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from app.core.db import get_db_instance
from app.core.security import get_password_hash


TEST_USERNAME = "test_inactive_user_xyz"
TEST_EMAIL = "test_inactive_xyz@example.com"
TEST_PASSWORD = "TestPass123!@#"


async def main():
    db = get_db_instance()

    # 1. Pastro nëse ekziston
    db.users.delete_many({"username": TEST_USERNAME})

    # 2. Krijo user INACTIVE
    result = db.users.insert_one({
        "username": TEST_USERNAME,
        "email": TEST_EMAIL,
        "full_name": "Test Inactive",
        "hashed_password": get_password_hash(TEST_PASSWORD),
        "role": "STANDARD",
        "account_type": "SOLO",
        "subscription_tier": "BASIC",
        "product_plan": "SOLO_PLAN",
        "subscription_status": "INACTIVE",
        "consent_to_process": True,
        "is_deleted": False,
    })
    user_id = result.inserted_id
    print(f"✅ User test u krijua: {user_id} (subscription_status=INACTIVE)")
    print()

    try:
        async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
            # 3. Login
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

            # 4. Test endpoints
            tests = [
                ("GET", "/api/v1/cases"),
                ("GET", "/api/v1/calendar/events"),
                ("GET", "/api/v1/finance/invoices"),
                ("GET", "/api/v1/finance/expenses"),
                ("GET", "/api/v1/archive/items"),
                ("GET", "/api/v1/users/me"),
                ("GET", "/api/v1/support/messages"),
            ]

            print("─" * 70)
            print(f"{'Endpoint':<40} {'Status':<10} {'Rezultat'}")
            print("─" * 70)

            leaks = []
            protected = []
            whitelist_ok = []

            for method, path in tests:
                try:
                    r = await client.request(method, path, headers=headers)
                    status = r.status_code
                    if path == "/api/v1/users/me" and status == 200:
                        result = "✅ Whitelist OK (profil)"
                        whitelist_ok.append(path)
                    elif status == 200:
                        result = "⚠️  LEAK — 200 OK"
                        leaks.append(path)
                    elif status in (401, 403, 402):
                        result = "✅ Bllokuar"
                        protected.append(path)
                    else:
                        result = f"⚠️  {status}"
                    print(f"{path:<40} {status:<10} {result}")
                except Exception as e:
                    print(f"{path:<40} ERROR: {e}")

            print("─" * 70)
            print()
            print(f"📊 REZULTATI:")
            print(f"   Të bllokuara:         {len(protected)}")
            print(f"   Whitelist OK:         {len(whitelist_ok)}")
            print(f"   LEAKS (200 OK):       {len(leaks)}")
            print()

            if leaks:
                print("🔴 LEAKS — këto endpoint-e duhet të mbrohen:")
                for p in leaks:
                    print(f"   - {p}")
            else:
                print("✅ ASNJË LEAK — sistemi i mbrojtur")

    finally:
        # 5. Pastro user test
        db.users.delete_one({"_id": user_id})
        print(f"\n🧹 User test u fshi.")


if __name__ == "__main__":
    asyncio.run(main())