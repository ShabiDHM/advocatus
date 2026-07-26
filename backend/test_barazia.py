from app.core.db import get_db_instance
from app.api.endpoints.laws import find_law_documents

db = get_db_instance()

print("=" * 60)
print("TESTING (Barazia para Ligjit) - Article 24")
print("=" * 60)

# Test (Barazia para Ligjit)
result = find_law_documents(db, '(Barazia para Ligjit)', '24')

print(f"Found {len(result)} documents for (Barazia para Ligjit), Article 24")
if result:
    for doc in result:
        print(f"  Article: {doc.get('article_number')}")
        print(f"  Law: {doc.get('law_title')}")
else:
    print("❌ No documents found")
    
    # Check if it exists in the Constitution
    print("\n" + "=" * 60)
    print("CHECKING CONSTITUTION FOR ARTICLE 24")
    print("=" * 60)
    
    constitution_docs = list(db.legal_knowledge_base.find({
        'law_title': {'$regex': 'Kushtetuta', '$options': 'i'},
        'article_number': {'$regex': '24', '$options': 'i'}
    }).limit(5))
    
    if constitution_docs:
        print(f"✅ Found {len(constitution_docs)} documents in Constitution for Article 24")
        for doc in constitution_docs:
            print(f"  Article: {doc.get('article_number')}")
            print(f"  Law: {doc.get('law_title')}")
            print(f"  Text preview: {doc.get('text', '')[:100]}...")
    else:
        print("❌ No Article 24 found in Constitution")
        