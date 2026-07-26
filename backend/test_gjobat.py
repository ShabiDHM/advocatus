from app.core.db import get_db_instance

db = get_db_instance()

print("=" * 60)
print("SEARCHING FOR 'GJOBAT' IN DATABASE")
print("=" * 60)

# Search for any law with "gjob" in title
print("\n=== LAWS CONTAINING 'gjob' in title ===")
docs = list(db.legal_knowledge_base.find({
    'law_title': {'$regex': 'gjob', '$options': 'i'}
}).limit(10))

if docs:
    for doc in docs:
        print(f"  Law: {doc.get('law_title')}")
        print(f"  Article: {doc.get('article_number')}")
        print("-" * 40)
else:
    print("  No laws found with 'gjob' in title")

# Search for any law with "gjob" in the article text
print("\n=== ARTICLES CONTAINING 'gjob' in text ===")
docs2 = list(db.legal_knowledge_base.find({
    'text': {'$regex': 'gjob', '$options': 'i'}
}).limit(10))

if docs2:
    for doc in docs2:
        print(f"  Law: {doc.get('law_title')}")
        print(f"  Article: {doc.get('article_number')}")
        print(f"  Text preview: {doc.get('text', '')[:100]}...")
        print("-" * 40)
else:
    print("  No articles found with 'gjob' in text")

# Search for Article 500 across all laws
print("\n=== ARTICLE 500 ACROSS ALL LAWS ===")
docs3 = list(db.legal_knowledge_base.find({
    'article_number': {'$regex': '500', '$options': 'i'}
}).limit(10))

if docs3:
    for doc in docs3:
        print(f"  Law: {doc.get('law_title')}")
        print(f"  Article: {doc.get('article_number')}")
        print(f"  Text preview: {doc.get('text', '')[:80]}...")
        print("-" * 40)
else:
    print("  No Article 500 found in any law")

# Show all distinct law titles with numbers (to help identify)
print("\n=== ALL LAW TITLES (first 20) ===")
titles = db.legal_knowledge_base.distinct('law_title')
for i, title in enumerate(sorted(titles)[:20]):
    print(f"  {i+1}. {title}")
    