# FILE: backend/app/services/debug_albanian_detection.py
# REWRITTEN FOR DECOUPLED V10.0 ARCHITECTURE

import logging
import os
import sys

# --- Path Setup ---
# This allows the script to be run directly and find the 'backend' package
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# --- Corrected Imports ---
from backend.app.services.albanian_language_detector import AlbanianLanguageDetector
from backend.app.config.albanian_feature_flags import AlbanianRAGFeatureFlags

# Set up detailed logging
logging.basicConfig(level=logging.INFO)
logging.getLogger().setLevel(logging.INFO) # Quieter for this test

def debug_routing_logic():
    """
    Tests the core routing components (language detector and feature flags)
    independently, simulating the logic from chat_service.py.
    """
    print("🐛 DEBUGGING ALBANIAN AI ROUTING LOGIC")
    print("=" * 60)
    
    # 1. Instantiate the components directly
    try:
        language_detector = AlbanianLanguageDetector()
        feature_flags = AlbanianRAGFeatureFlags()
        print("✅ Components instantiated successfully.")
    except Exception as e:
        print(f"❌ FAILED to instantiate components: {e}")
        return

    # 2. Configure feature flags for this test run
    feature_flags.enable_for_testing() # Use the override for predictable results
    
    print("\n🔧 Feature flags override is ACTIVE for this test run.")
    
    # 3. Define test cases
    test_queries = [
        ("Cila është data e seancës së ardhshme?", "albanian_user", "req_001"),
        ("Listoni dëshmitarët në këtë çështje", "albanian_user", "req_002"),
        ("What is the court date?", "english_user", "req_003"),
        ("A simple hello", "english_user", "req_004"),
        ("Përshëndetje", "albanian_user", "req_005"),
    ]
    
    print("\n🔍 ANALYZING ROUTING DECISIONS:")
    print("-" * 40)
    
    for query, user_id, request_id in test_queries:
        print(f"\n📝 Query: '{query}'")
        
        # --- Simulate the exact logic from chat_service.py ---
        
        # Step A: Check feature flags
        flag_enabled = feature_flags.is_enabled_for_request(user_id, request_id)
        print(f"   [1] Feature Flag Check: {'ENABLED' if flag_enabled else 'DISABLED'}")
        
        # Step B: Check language detection
        is_albanian = language_detector.is_albanian(query)
        print(f"   [2] Language Check:     {'ALBANIAN' if is_albanian else 'NOT ALBANIAN'}")
        
        # Step C: Final Decision
        should_route_to_albanian_ai = flag_enabled and is_albanian
        
        decision = "✅ ROUTE to Albanian RAG Service" if should_route_to_albanian_ai else "❌ FALLBACK to Standard Chat"
        print(f"   ------------------------------------")
        print(f"   DECISION: {decision}")

    print("\n" + "=" * 60)
    print("✅ Debug script finished.")


if __name__ == "__main__":
    # To run this script directly:
    # python -m backend.app.services.debug_albanian_detection
    debug_routing_logic()