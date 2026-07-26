from app.core.db import get_db_instance
from app.api.endpoints.laws import find_law_documents

db = get_db_instance()

print("=" * 60)
print("TESTING ARTICLE 92 WITH FIND_LAW_DOCUMENTS")
print("=" * 60)

# Test Article 92
result = find_law_documents(db, 'Ligji Nr. 03/L-006', '92')

print(f"Found {len(result)} documents for Article 92")
if result:
    for doc in result:
        print(f"  Article: {doc.get('article_number')}")
        print(f"  Law: {doc.get('law_title')}")
        print(f"  Text preview: {doc.get('text', '')[:100]}...")
        print("-" * 40)
else:
    print("❌ No documents found for Article 92")

print("\n" + "=" * 60)
print("TESTING ARTICLE 147 (should work)")
print("=" * 60)

# Test Article 147
result2 = find_law_documents(db, 'Ligji Nr. 03/L-006', '147')

print(f"Found {len(result2)} documents for Article 147")
if result2:
    for doc in result2:
        print(f"  Article: {doc.get('article_number')}")
        print(f"  Law: {doc.get('law_title')}")
else:
    print("❌ No documents found for Article 147")

print("\n" + "=" * 60)
print("DEBUG: What variations does _get_law_code_variations generate?")
print("=" * 60)

from app.api.endpoints.laws import _get_law_code_variations
variations = _get_law_code_variations('Ligji Nr. 03/L-006')
print(f"Variations generated: {variations}")