# FILE: backend/test_ai_improve.py
# Diagnostikues: teston endpoint-in /documents/ai-improve
# Ekzekuto: python test_ai_improve.py

import os
import sys
import json
import requests

# ═══════════════════════════════════════════════════════════════════
# KONFIGURIMI
# ═══════════════════════════════════════════════════════════════════

API_BASE = os.getenv("API_BASE", "http://localhost:8000/api/v1")
TOKEN = os.getenv("TEST_TOKEN", "")  # Vendos tokenin direkt ose përmes env

if not TOKEN:
    print("❌ Mungon TEST_TOKEN.")
    print("   Zgjidhje 1: $env:TEST_TOKEN='eyJ...'  (në PowerShell)")
    print("   Zgjidhje 2: Vendos TOKEN = 'eyJ...'  brenda file-it")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════
# TEKSTI TESTUES
# ═══════════════════════════════════════════════════════════════════

TEST_TEXT = (
    "Prokurorja Fikrije Sylejmani ka ngritur aktakuzen ne "
    "lenden PP.II.nr. 122/24F sipas Neni 31 te KPRK-se. "
    "Ky veprim eshte ne kundershtim me ligjin. "
    "Dëmi i shkaktuar vlerësohet në 5000 EUR dhe datë 30.01.2024."
)

# ═══════════════════════════════════════════════════════════════════
# THIRRJA
# ═══════════════════════════════════════════════════════════════════

url = f"{API_BASE}/cases/documents/ai-improve"
print(f"📡 POST {url}")
print(f"📝 Input: {len(TEST_TEXT)} chars")
print("─" * 70)

try:
    r = requests.post(
        url,
        json={"text": TEST_TEXT},
        headers={"Authorization": f"Bearer {TOKEN}"},
        stream=True,
        timeout=120,
    )
except Exception as e:
    print(f"❌ Lidhja dështoi: {e}")
    sys.exit(1)

print(f"Status: {r.status_code}")
print("─" * 70)

if r.status_code != 200:
    print(f"❌ Gabim HTTP: {r.text[:500]}")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════
# LEXO SSE
# ═══════════════════════════════════════════════════════════════════

for line in r.iter_lines():
    if not line:
        continue
    decoded = line.decode("utf-8")

    if decoded.startswith("data: "):
        payload_str = decoded[6:]
        if payload_str == "[DONE]":
            print("✅ [DONE]")
            break
        try:
            evt = json.loads(payload_str)
            event_type = evt.get("event", "?")

            if event_type == "step_started":
                print(f"🔄 {evt.get('step_title', evt.get('step_key'))}")

            elif event_type == "validation_completed":
                print(f"🛡️  Validation: severity={evt.get('severity')}, "
                      f"issues={evt.get('total_issues')}")

            elif event_type == "completed":
                result = evt.get("result", {})
                print("─" * 70)
                print("✅ COMPLETED")
                print(f"   chars: {result.get('input_chars')} → {result.get('content_chars')} "
                      f"({result.get('ratio_pct')}%)")
                print(f"   duration: {result.get('duration_sec')}s")
                print(f"   tokens: in={result.get('input_tokens')}, out={result.get('output_tokens')}")
                print(f"   cost≈ ${result.get('cost_estimate_usd')}")

                validation = result.get("validation", {})
                print(f"   guard: {validation.get('severity')} "
                      f"({validation.get('total_issues')} issues, "
                      f"{validation.get('kept_tokens')}/{validation.get('total_tokens')} tokens kept)")

                missing = validation.get("missing_tokens", [])
                if missing:
                    print(f"   ⚠️  TOKENS HUMBUR: {missing}")

                print("─" * 70)
                print("📄 PËRMIRËSUAR:")
                print(result.get("content", "")[:2000])
                print("─" * 70)

            elif event_type == "error":
                print(f"❌ ERROR: {evt.get('message')}")

            else:
                print(f"❓ {event_type}: {payload_str[:200]}")

        except json.JSONDecodeError:
            print(f"⚠️  JSON i pavlefshëm: {payload_str[:200]}")
    else:
        print(f"   {decoded}")
        