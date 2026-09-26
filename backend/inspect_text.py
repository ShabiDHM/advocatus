# inspect_text.py
from bson import ObjectId
from app.core.db import get_db
import re

db = get_db()

# deep_seek_kallxim.docx
doc = db.documents.find_one({"_id": ObjectId("6ab42cb6b6e7f311be56c2af")})
if not doc:
    print("❌ Doc nuk u gjet")
    exit(1)

text = doc.get("content") or doc.get("extracted_text") or ""
print(f"Total chars: {len(text)}")
print()

# A ka fjalët kyçe?
for kw in ["GRUPI", "NAZLIE", "BALA", "DOBËRDOLANI", "DOBERDOLANI", "SABIT"]:
    print(f"  '{kw}': {'PO' if kw in text else 'JO'}")

print()
print("=" * 70)
print("Rreshtat me NAZLIE / DOBËRDOLANI / GRUPI (konteksti):")
print("=" * 70)

lines = text.split("\n")
print(f"Total rreshta: {len(lines)}")
print()

for i, line in enumerate(lines):
    upper = line.upper()
    if "NAZLIE" in upper or "DOBËRDOLANI" in upper or "DOBERDOLANI" in upper or "GRUPI" in upper or "SABIT" in upper:
        print(f"[Line {i}] len={len(line)}")
        print(f"  {repr(line[:250])}")
        print()

print("=" * 70)
print("Të gjitha rreshtat që fillojnë me numër + pika:")
print("=" * 70)
numbered = re.findall(r'^\s*\d+\.\s+.{0,80}', text, re.MULTILINE)
print(f"Gjetur {len(numbered)} rreshta të numëruar (regex origjinal)")
for line in numbered[:20]:
    print(f"  {repr(line[:100])}")