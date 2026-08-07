# FILE: backend/scripts/diagnose_titles.py
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

from app.core.db import get_db_instance

def diagnose():
    db = get_db_instance()
    
    print("\n================ MONGODB DIAGNOSTIC REPORT ================")
    
    all_categories = db.legal_knowledge_base.distinct("category")
    print(f"Categories present in MongoDB: {all_categories}")
    
    for cat in list(set(all_categories + [None, "academic", "caselaw"])):
        query = {"category": cat} if cat is not None else {"category": {"$exists": False}}
        sources = db.legal_knowledge_base.distinct("source", query)
        titles = db.legal_knowledge_base.distinct("law_title", query)
        print(f"\nCategory: '{cat}'")
        print(f"  Distinct Sources ({len(sources)}): {sources[:5]}")
        print(f"  Distinct Titles Count: {len(titles)}")
        print(f"  Sample Titles: {titles[:5]}")

    print("\n===========================================================\n")

if __name__ == "__main__":
    diagnose()