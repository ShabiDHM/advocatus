# backend/scripts/test_truncate_draft.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.services.document_review.verify.context_builders import _truncate_draft

# Default behavior ruhet
big = "X" * 100_000
out = _truncate_draft(big)  # default 60000
assert len(out) < 100_000, "Duhet truncate"
assert "karaktere të hequr" in out
print(f"OK default: {len(big)} → {len(out)} chars")

# max_chars i vogël nuk prodhon dyfishim
small = "Y" * 3000
out_small = _truncate_draft(small, max_chars=2000)
# Nuk duhet të ketë dyfishim; pritet head (min(45000, 2000)=2000) + tail (0)
assert out_small.count("Y") <= 3000, f"Dyfishim! count={out_small.count('Y')}"
assert "karaktere të hequr" in out_small
print(f"OK small: {len(small)} → {len(out_small)} chars")

print("\nTË GJITHA TESTET KALUAN")