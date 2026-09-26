# FILE: backend/verify_llm_models.py
# Verifikon se Claude/Anthropic nuk përdoret kudo në backend + frontend.
# Ekzekuto: python verify_llm_models.py   (nga backend/)
# Fshi pas përdorimit.

import re
from pathlib import Path

BACKEND = Path(__file__).parent.resolve()
ROOT = BACKEND.parent
FRONTEND = ROOT / "frontend"

# Token-ët për Claude/Anthropic + modele të tjera jo-DeepSeek/GPT4o-mini
CLAUDE_TOKENS = [
    "claude",
    "anthropic",
    "sonnet",
    "haiku",
    "opus",
    "claude-3",
    "claude-sonnet",
    "claude-opus",
    "claude-haiku",
]

# Modele që DUHET të shfaqen
ALLOWED_MODELS = [
    "deepseek/deepseek-chat",
    "openai/gpt-4o-mini",
    "openai/text-embedding-3-small",  # embedding
]

# Folders që skanohen
SCAN_DIRS = [
    (BACKEND / "app", "*.py", "BACKEND / app"),
    (BACKEND / "_tests_dev", "*.py", "BACKEND / _tests_dev"),
    (FRONTEND / "src", "*.ts", "FRONTEND / src .ts"),
    (FRONTEND / "src", "*.tsx", "FRONTEND / src .tsx"),
]

# Fjalë që lejohen brenda kontekstit (jo referenca model)
ALLOWLIST_PHRASES = [
    "claude",  # nëse ka "no claude" ose "hequr claude" në komente
]

# Skedarë që lejohen të përmendin Claude (dokumentacion historik)
ALLOWLIST_FILES = [
    "verify_llm_models.py",       # ky file
    "llm_client.py",               # header comment V88.0
]


def _is_allowlisted_file(rel: str) -> bool:
    for name in ALLOWLIST_FILES:
        if name in rel:
            return True
    return False


def scan(base: Path, pattern: str, label: str):
    print(f"\n### {label}")
    print("-" * 78)
    if not base.exists():
        print("  [SKIP — nuk ekziston]")
        return 0

    hits = 0
    for f in base.rglob(pattern):
        parts = set(f.parts)
        if "__pycache__" in parts or "_legacy" in parts or "node_modules" in parts:
            continue
        try:
            rel = str(f.relative_to(ROOT))
        except ValueError:
            rel = str(f)
        if _is_allowlisted_file(rel):
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            s = line.strip()
            if s.startswith("#") or s.startswith("//"):
                continue
            low = s.lower()
            for tok in CLAUDE_TOKENS:
                if re.search(rf"\b{re.escape(tok)}\b", low):
                    print(f"  [{tok}] {rel}:{i}: {s[:120]}")
                    hits += 1
                    break
    if hits == 0:
        print("  ✅ Pa referenca ndaj Claude/Anthropic.")
    return hits


def scan_models():
    """Konfirmon se modelet e lejuara shfaqen."""
    print("\n### KONFIRMIM I MODELEVE TË LEJUARA")
    print("-" * 78)
    llm_path = BACKEND / "app" / "services" / "llm" / "llm_client.py"
    if not llm_path.exists():
        print(f"  ❌ Nuk gjendet {llm_path}")
        return
    text = llm_path.read_text(encoding="utf-8", errors="ignore")
    for m in ALLOWED_MODELS:
        if m in text:
            print(f"  ✅ {m}")
        else:
            print(f"  ⚠️  {m} — NUK u gjet")


def main():
    print("=" * 78)
    print("VERIFIKIM — Claude / Anthropic në aplikacion")
    print("=" * 78)

    total = 0
    for base, pat, label in SCAN_DIRS:
        total += scan(base, pat, label)

    scan_models()

    print("\n" + "=" * 78)
    if total == 0:
        print("✅ PASTER — Claude/Anthropic nuk përdoret askund.")
        print("   Vetëm DeepSeek + GPT-4o-mini + text-embedding-3-small.")
    else:
        print(f"⚠️  {total} referenca — shqyrto para commit-it.")
    print("=" * 78)


if __name__ == "__main__":
    main()