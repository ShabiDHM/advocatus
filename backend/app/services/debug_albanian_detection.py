# FILE: backend/app/services/debug_albanian_detection.py
# REWRITTEN FOR DECOUPLED V10.0 ARCHITECTURE

import logging
import os

# Corrected relative imports, verified in the previous step.
from .albanian_language_detector import AlbanianLanguageDetector
from ..config.albanian_feature_flags import AlbanianRAGFeatureFlags

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
        # PHOENIX PROTOCOL CURE: Instantiate the class. The debug script will call the class method via the instance.
        language_detector = AlbanianLanguageDetector()
        feature_flags = AlbanianRAGFeatureFlags()
        print("✅ Components instantiated successfully.")
    except Exception as e:
        print(f"❌ FAILED to instantiate components: {e}")
        return
    
    print(f"\n🔧 Feature flags status from environment: DEV_MODE={feature_flags.dev_mode_enabled}")
    
    # 2. Define test cases
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
        # PHOENIX PROTOCOL CURE: Changed the method call from the non-existent 'is_albanian' to the correct 'detect_language'.
        is_albanian = language_detector.detect_language(query)
        print(f"   [2] Language Check:     {'ALBANIAN' if is_albanian else 'NOT ALBANIAN'}")
        
        # Step C: Final Decision
        should_route_to_albanian_ai = flag_enabled and is_albanian
        
        decision = "✅ ROUTE to Albanian RAG Service" if should_route_to_albanian_ai else "❌ FALLBACK to Standard Chat"
        print(f"   ------------------------------------")
        print(f"   DECISION: {decision}")

    print("\n" + "=" * 60)
    print("✅ Debug script finished.")


if __name__ == "__main__":
    # PHOENIX PROTOCOL CURE: To ensure the feature flag is on for this test,
    # we programmatically set the environment variable that enables DEV MODE.
    # This is the correct way to control the feature flag's behavior for testing.
    print("--- OVERRIDING ENVIRONMENT FOR TEST RUN ---")
    os.environ['ALBANIAN_AI_DEV_MODE'] = 'true'
    
    # To run this script directly and correctly:
    # python -m app.services.debug_albanian_detection
    debug_routing_logic()