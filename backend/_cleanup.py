from app.core.db import get_db

db = get_db()

old_ids = [
    '6aa9ab04bbdf3ff0b2edcc00',
    '6aa9bea4bbdf3ff0b2edcc49',
]

result = db.user_vectors.delete_many({"document_id": {"$in": old_ids}})
print(f"Fshirë: {result.deleted_count} chunks")

# Verifiko pastrimin
remaining = db.user_vectors.count_documents({"file_name": "deep_seek_kallxim.docx"})
print(f"Chunks të mbetur për 'deep_seek_kallxim.docx': {remaining}")

# Kontrollo statuset
from app.models.document import DocumentStatus
print(f"Statuset e disponueshme: {[s.value for s in DocumentStatus]}")