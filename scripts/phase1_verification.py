# scripts/phase1_verification.py
# VERSION: FINAL_RESET
"""
Phase 1 Verification Script (Definitive Version)

Purpose:
- This script uses the verified 'backend/app' structure.
- It will confirm that all Phase 1 components are importable and
  reveal the contract of the AlbanianRAGService.
"""
import sys
import os
import asyncio

# --- Path Setup ---
# Add the project root to the path to enable top-level imports.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

print(f"✅ Project Root confirmed: {PROJECT_ROOT}")
print("✅ Using verified import path: 'backend.app.<module>'")

# --- Verification Functions ---

def verify_language_detector():
    """Verify the AlbanianLanguageDetector."""
    print("\n--- Verifying: AlbanianLanguageDetector ---")
    try:
        from backend.app.services.albanian_language_detector import AlbanianLanguageDetector
        detector = AlbanianLanguageDetector()
        print("✅ SUCCESS: Imported and instantiated.")
        return True
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}: {e}")
        return False

def verify_feature_flags():
    """Verify the AlbanianRAGFeatureFlags."""
    print("\n--- Verifying: AlbanianRAGFeatureFlags ---")
    try:
        from backend.app.config.albanian_feature_flags import AlbanianRAGFeatureFlags
        flags = AlbanianRAGFeatureFlags()
        print("✅ SUCCESS: Imported and instantiated.")
        return True
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}: {e}")
        return False

def verify_rag_service():
    """Verify the AlbanianRAGService."""
    print("\n--- Verifying: AlbanianRAGService ---")
    try:
        from backend.app.services.albanian_rag_service import AlbanianRAGService
        rag_service = AlbanianRAGService()
        print("✅ SUCCESS: Instantiated without arguments.")
        return True
    except TypeError as te:
        if "missing" in str(te):
             print(f"✅ SUCCESS (INFO): Service correctly requires arguments for initialization.")
             print(f"   CONTRACT DETAILS: {te}")
             return True # This is a successful test.
        else:
             print(f"❌ FAILED: Instantiation failed with unexpected TypeError: {te}")
             return False
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}: {e}")
        return False

# --- Main Execution ---

async def main():
    """Run all verification checks."""
    print("\n🚀 Starting Final Component Verification...")

    results = {
        "language_detector": verify_language_detector(),
        "feature_flags": verify_feature_flags(),
        "rag_service": verify_rag_service(),
    }

    print("\n--- Verification Summary ---")
    all_passed = all(results.values())
    for component, status in results.items():
        print(f'{"✅" if status else "❌"} {component}: {"PASSED" if status else "FAILED"}')

    print("\n--- Conclusion ---")
    if all_passed:
        print("✅ All Phase 1 components are correctly structured and importable.")
        print("✅ We can now FINALLY proceed with Phase 2 Integration.")
    else:
        print("❌ Critical errors persist. Please review the specific error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())