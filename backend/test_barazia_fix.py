from app.core.db import get_db_instance
from app.api.endpoints.laws import find_law_documents

db = get_db_instance()

print("=" * 60)
print("TESTING (Barazia para Ligjit) WITH MAPPING")
print("=" * 60)

result = find_law_documents(db, '(Barazia para Ligjit)', '24')

print(f"Found {len(result)} documents")
for doc in result:
    print(f"  Article: {doc.get('article_number')}")
    print(f"  Law: {doc.get('law_title')}")
    print(f"  Text: {doc.get('text', '')[:80]}...")