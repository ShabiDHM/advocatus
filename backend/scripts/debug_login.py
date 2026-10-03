# FILE: backend/scripts/debug_login.py
"""Diagnozë e plotë për login-in — capture traceback."""
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.db import get_db_instance
from app.core import security
from app.core.security import get_password_hash
from app.services import user_service

TEST_USERNAME = "test_debug_login_xyz"
TEST_EMAIL = "test_debug_login_xyz@example.com"
TEST_PASSWORD = "TestPass123!@#"

db = get_db_instance()
db.users.delete_many({"username": TEST_USERNAME})

print("=" * 70)
print("1. Krijo user test")
print("=" * 70)
try:
    user_id = db.users.insert_one({
        "username": TEST_USERNAME,
        "email": TEST_EMAIL,
        "full_name": "Test Debug",
        "hashed_password": get_password_hash(TEST_PASSWORD),
        "role": "STANDARD",
        "account_type": "SOLO",
        "subscription_tier": "BASIC",
        "product_plan": "SOLO_PLAN",
        "subscription_status": "INACTIVE",
        "consent_to_process": True,
        "is_deleted": False,
    }).inserted_id
    print(f"OK — user_id={user_id}")
except Exception as e:
    print(f"FAIL: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print()
    print("=" * 70)
    print("2. get_user_by_username")
    print("=" * 70)
    try:
        user = user_service.get_user_by_username(db, TEST_USERNAME)
        print(f"OK — user={user}")
    except Exception as e:
        print(f"FAIL: {e}")
        traceback.print_exc()

    print()
    print("=" * 70)
    print("3. authenticate")
    print("=" * 70)
    try:
        authenticated = user_service.authenticate(db, username=TEST_USERNAME, password=TEST_PASSWORD)
        print(f"OK — authenticated={authenticated}")
        if authenticated:
            print(f"   role={authenticated.role}")
            print(f"   id={authenticated.id}")
    except Exception as e:
        print(f"FAIL: {e}")
        traceback.print_exc()
        authenticated = None

    print()
    print("=" * 70)
    print("4. security.check_login_attempts (Redis)")
    print("=" * 70)
    try:
        ok = security.check_login_attempts(str(user_id))
        print(f"OK — check={ok}")
    except Exception as e:
        print(f"FAIL: {e}")
        traceback.print_exc()

    print()
    print("=" * 70)
    print("5. create_access_token")
    print("=" * 70)
    try:
        if authenticated:
            token = security.create_access_token(data={"id": str(authenticated.id), "role": authenticated.role})
            print(f"OK — token={token[:50]}...")
        else:
            print("SKIP — no authenticated user")
    except Exception as e:
        print(f"FAIL: {e}")
        traceback.print_exc()

    print()
    print("=" * 70)
    print("6. reset_login_attempts (Redis)")
    print("=" * 70)
    try:
        security.reset_login_attempts(str(user_id))
        print("OK")
    except Exception as e:
        print(f"FAIL: {e}")
        traceback.print_exc()

finally:
    db.users.delete_one({"_id": user_id})
    print()
    print("User test u fshi.")