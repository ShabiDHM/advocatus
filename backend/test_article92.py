from app.core.db import get_db_instance
import re

db = get_db_instance()

print("=" * 60)
print("TESTING ARTICLE 92 SEARCH")
print("=" * 60)

raw_law_title = "Ligji Nr. 03/L-006"
raw_article_num = "92"

# Step 1: Article variants
clean_art = str(raw_article_num).replace('Neni', '').replace('neni', '').replace('.', '').strip()
art_variants = [clean_art, f"{clean_art}.", f"Neni {clean_art}", f"NENI {clean_art}"]
print(f"Article variants: {art_variants}")

# Step 2: Try the law code match
law_num_match = re.search(r'\b(\d{2,4}[\/\-][L\d\-]+(?:\d+)?)\b', raw_law_title, re.I)
if law_num_match:
    law_code = law_num_match.group(1)
    print(f"Law code extracted: '{law_code}'")
    
    query = {
        "law_title": {"$regex": re.escape(law_code), "$options": "i"},
        "article_number": {"$in": art_variants}
    }
    print(f"Query: {query}")
    
    result = db.legal_knowledge_base.find_one(query)
    if result:
        print(f"✅ FOUND! Article: {result.get('article_number')}")
        print(f"   Law title: {result.get('law_title')}")
    else:
        print("❌ NOT FOUND with law code match")
else:
    print("❌ No law code extracted")

# Step 3: Try just by article number
print("\n" + "=" * 60)
print("TESTING ARTICLE ONLY SEARCH")
print("=" * 60)

result2 = db.legal_knowledge_base.find_one({"article_number": "92"})
if result2:
    print(f"✅ FOUND by article only!")
    print(f"   Article: {result2.get('article_number')}")
    print(f"   Law title: {result2.get('law_title')}")
else:
    print("❌ NOT FOUND by article only")

# Step 4: Try with law title variation (space instead of slash)
print("\n" + "=" * 60)
print("TESTING WITH SPACE VARIATION")
print("=" * 60)

query3 = {
    "law_title": {"$regex": "03 L-006", "$options": "i"},
    "article_number": {"$in": art_variants}
}
print(f"Query: {query3}")

result3 = db.legal_knowledge_base.find_one(query3)
if result3:
    print(f"✅ FOUND! Article: {result3.get('article_number')}")
    print(f"   Law title: {result3.get('law_title')}")
else:
    print("❌ NOT FOUND with space variation")

# Step 5: Show what's actually in the database for this law
print("\n" + "=" * 60)
print("SAMPLE DOCUMENTS IN DATABASE FOR 03/L-006")
print("=" * 60)

sample_docs = list(db.legal_knowledge_base.find({
    'law_title': {'$regex': '03 L-006', '$options': 'i'}
}).limit(5))

for doc in sample_docs:
    print(f"  Article: {doc.get('article_number')} | Law: {doc.get('law_title')[:50]}...")