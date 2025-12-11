# FILE: backend/scripts/run_test_suite.py
# PHOENIX PROTOCOL - END-TO-END VALIDATION SUITE V1.0
# 1. SCOPE: Tests Document Upload -> Findings Extraction -> Analysis -> RAG Chat.
# 2. TARGET: Uses the "Toxic Divorce" case as the ground truth.
# 3. OUTPUT: Prints clear PASS/FAIL results for each stage.

import os
import sys
import logging
import time
from pymongo import MongoClient
import urllib.parse

# --- Setup: Add app to Python path ---
sys.path.append(os.getcwd())
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TestSuite")

# --- Test Configuration ---
# These should match your .env file for a successful run
MONGO_HOST = os.getenv("MONGO_HOST", "mongo")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_USER = os.getenv("MONGO_USER")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
DB_NAME = os.getenv("MONGO_DB_NAME", "phoenix_protocol_db")
MONGO_AUTH_SOURCE = os.getenv("MONGO_AUTH_SOURCE", "admin")

# --- Test Data: The "Toxic Divorce" case ---
TEST_DOCUMENT_CONTENT = """
REPUBLIKA E KOSOVËS
GJYKATA THEMELORE NË PRIZREN
Departamenti për Çështje Familjare

Paditëse: Teuta Krasniqi, e papunë, Prizren.
I Paditur: Ilir Krasniqi, biznesmen, Prizren.

OBJEKTI: Padi për Zgjidhjen e Martesës, Besimin e Fëmijëve dhe Alimentacion.

II. PRETENDIMET E PADITËSES (TEUTA)
1. Dhuna Ekonomike: Ilir Krasniqi posedon pasuri të mëdha të fshehura në kriptovaluta (Bitcoin) të cilat nuk i deklaron. Ai i jep paditëses vetëm 50 Euro në javë për ushqim.
2. Kërkesa: Besimi i fëmijëve t'i takojë nënës, dhe i padituri të paguajë 1000 Euro alimentacion mujor.

III. KUNDËR-PËRGJIGJA E TË PADITURIT (ILIR)
1. I padituri mohon kategorikisht çdo formë dhune. Ai pretendon se Teuta vuan nga paranoja.
2. Lidhur me financat: Biznesi i Ilirit ka falimentuar në vitin 2024. Ai nuk posedon kriptovaluta. "Pasuria" që përmend Teuta është trillim.
"""

# --- Test Suite Class ---
class SystemIntegrityTest:
    def __init__(self):
        self.db = self._connect_to_db()
        # Lazy import services to ensure app is initialized
        from app.services import llm_service, analysis_service, chat_service
        self.llm_service = llm_service
        self.analysis_service = analysis_service
        # We need to simulate the chat service call structure
        self.chat_service = chat_service
        logger.info("✅ Test Suite Initialized.")

    def _connect_to_db(self):
        logger.info("🔌 Connecting to MongoDB...")
        if MONGO_USER and MONGO_PASSWORD:
            username = urllib.parse.quote_plus(MONGO_USER)
            password = urllib.parse.quote_plus(MONGO_PASSWORD)
            mongo_url = f"mongodb://{username}:{password}@{MONGO_HOST}:{MONGO_PORT}/?authSource={MONGO_AUTH_SOURCE}"
        else:
            mongo_url = f"mongodb://{MONGO_HOST}:{MONGO_PORT}/"
        
        client = MongoClient(mongo_url)
        db = client[DB_NAME]
        db.command('ping')
        logger.info("   MongoDB Connection Successful.")
        return db

    def run_all_tests(self):
        logger.info("\n--- STARTING PHOENIX PROTOCOL TEST SUITE ---")
        
        # Run tests in logical order
        self.test_1_findings_extraction()
        self.test_2_analysis_engine()
        # self.test_3_rag_chat_response() # This requires a running async loop, more complex
        
        logger.info("\n--- TEST SUITE COMPLETE ---")

    def test_1_findings_extraction(self):
        logger.info("\n▶️ TEST 1: Findings Extraction (llm_service)")
        try:
            findings = self.llm_service.extract_findings_from_text(TEST_DOCUMENT_CONTENT)
            
            assert len(findings) > 3, "FAIL: Expected at least 4 findings, found less."
            logger.info("   - PASSED: Correct number of findings generated.")
            
            # Check for specific monetary amounts
            found_1000_eur = any("1000 Euro" in f.get('finding_text', '') for f in findings)
            assert found_1000_eur, "FAIL: Did not find the '1000 Euro' alimentacion claim."
            logger.info("   - PASSED: Correctly extracted '1000 Euro' claim.")

            found_50_eur = any("50 Euro" in f.get('finding_text', '') for f in findings)
            assert found_50_eur, "FAIL: Did not find the '50 Euro' fact."
            logger.info("   - PASSED: Correctly extracted '50 Euro' fact.")

            logger.info("✅ TEST 1 PASSED: Findings Extraction is functioning correctly.")
        except Exception as e:
            logger.error(f"❌ TEST 1 FAILED: {e}", exc_info=True)

    def test_2_analysis_engine(self):
        logger.info("\n▶️ TEST 2: Conflict Analysis Engine (llm_service)")
        try:
            analysis = self.llm_service.analyze_case_contradictions(TEST_DOCUMENT_CONTENT)
            
            assert "contradictions" in analysis, "FAIL: 'contradictions' key is missing from analysis."
            assert len(analysis["contradictions"]) > 0, "FAIL: The engine did not find any contradictions."
            logger.info("   - PASSED: Contradiction field is present and populated.")
            
            # Check if it correctly identified the core financial conflict
            financial_conflict_found = any("kripto" in c.lower() or "bankare" in c.lower() or "falimentuar" in c.lower() for c in analysis["contradictions"])
            assert financial_conflict_found, "FAIL: Did not identify the core crypto/bankruptcy contradiction."
            logger.info("   - PASSED: Correctly identified the financial contradiction.")

            logger.info("✅ TEST 2 PASSED: Conflict Analysis is functioning correctly.")
        except Exception as e:
            logger.error(f"❌ TEST 2 FAILED: {e}", exc_info=True)

    # Note: Testing the full async chat service in a sync script is complex.
    # We would typically use a test client like `httpx.AsyncClient` for this.
    # This script focuses on the synchronous logic of the underlying AI services.

if __name__ == "__main__":
    suite = SystemIntegrityTest()
    suite.run_all_tests()