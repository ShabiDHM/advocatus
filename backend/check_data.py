from app.core.db import get_db_instance

db = get_db_instance()

# Find Article 92 specifically
article_92 = db.legal_knowledge_base.find_one({
    'law_title': {'$regex': '03 L-006', '$options': 'i'},
    'article_number': {'$regex': '92', '$options': 'i'}
})

print("=" * 60)
print("ARTICLE 92 DETAILS:")
print("=" * 60)
if article_92:
    print(f"  article_number: '{article_92.get('article_number')}' (type: {type(article_92.get('article_number')).__name__})")
    print(f"  law_title: '{article_92.get('law_title')}'")
    print(f"  text preview: {article_92.get('text', '')[:100]}...")
else:
    print("❌ Article 92 not found")

# Show all article number formats for this law (first 20)
print("\n" + "=" * 60)
print("SAMPLE ARTICLE NUMBER FORMATS:")
print("=" * 60)
docs = list(db.legal_knowledge_base.find({
    'law_title': {'$regex': '03 L-006', '$options': 'i'}
}).limit(20))

for doc in docs:
    print(f"  '{doc.get('article_number')}'")