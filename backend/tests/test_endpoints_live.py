# FILE: backend/tests/test_endpoints_live.py
# PHOENIX PROTOCOL - LIVE ENDPOINT TESTS V1.6
#
# V1.6: Teste për repeals (Option B).
#   - L13: /titles kthen repealed_statutes me detaje
#   - L14: /by-title për ligj të shfuqizuar → warning
#   - L15: /article për ligj të shfuqizuar → warning
#
# V1.5: Diagnostifikim i detajuar për L8-pdf.
# V1.4: Route discovery via openapi + PDF 500 → FAIL.
# V1.3: FIX bug në listim rrugësh.
# V1.2: Monton router-at direkt.
# V1.1: Teste për N1 (Neni 0) + N2 (junk titles).

import os
import sys
import traceback
from typing import List, Tuple, Optional, Any

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


# ═══════════════════════════════════════════════════════════════════════════
# APP SETUP
# ═══════════════════════════════════════════════════════════════════════════

APP = None
APP_ERROR = ""
APP_SOURCE = ""
LAWS_PREFIX = "/api/laws"


def _try_import_routers() -> Tuple[bool, str]:
    global _laws_query_router, _laws_pdf_router, _laws_audit_router
    try:
        from app.api.endpoints.laws_pkg.laws_query_router import router as qr
        _laws_query_router = qr
    except Exception as e:
        return False, f"laws_query_router import failed: {type(e).__name__}: {e}"

    try:
        from app.api.endpoints.laws_pkg.laws_pdf_router import router as pr
        _laws_pdf_router = pr
    except Exception as e:
        return False, f"laws_pdf_router import failed: {type(e).__name__}: {e}"

    try:
        from app.api.endpoints.laws_pkg.laws_audit_router import router as ar
        _laws_audit_router = ar
    except Exception:
        _laws_audit_router = None

    return True, ""


def _build_test_app():
    global APP, APP_ERROR, APP_SOURCE

    ok, err = _try_import_routers()
    if not ok:
        APP_ERROR = f"Router imports failed: {err}"
        return False

    try:
        from fastapi import FastAPI
        test_app = FastAPI(title="Laws Library Test App")

        test_app.include_router(_laws_query_router, prefix=LAWS_PREFIX)
        test_app.include_router(_laws_pdf_router, prefix=LAWS_PREFIX)
        if _laws_audit_router is not None:
            test_app.include_router(_laws_audit_router, prefix=LAWS_PREFIX)

        APP = test_app
        APP_SOURCE = "direct-mount"

        from app.api.endpoints.dependencies import get_current_user

        def override_get_current_user():
            return {
                "_id": "test-user-live",
                "id": "test-user-live",
                "username": "test-user",
                "role": "admin",
            }

        APP.dependency_overrides[get_current_user] = override_get_current_user
        return True

    except Exception as e:
        APP_ERROR = f"Test app build failed: {type(e).__name__}: {e}\n{traceback.format_exc()}"
        return False


# ═══════════════════════════════════════════════════════════════════════════
# ROUTE DISCOVERY
# ═══════════════════════════════════════════════════════════════════════════

def _get_openapi_paths() -> List[Tuple[str, str]]:
    try:
        schema = APP.openapi()
        paths_obj = schema.get("paths", {})
    except Exception:
        return []

    result: List[Tuple[str, str]] = []
    for path, methods_dict in paths_obj.items():
        if not path.startswith(LAWS_PREFIX):
            continue
        methods = [
            m.upper() for m in methods_dict.keys()
            if m.upper() not in ("HEAD", "OPTIONS")
        ]
        if not methods:
            continue
        methods_str = ",".join(sorted(methods))
        result.append((path, methods_str))
    result.sort()
    return result


def _get_laws_paths_set() -> set:
    return {p for p, _ in _get_openapi_paths()}


# ═══════════════════════════════════════════════════════════════════════════
# TEST FRAMEWORK
# ═══════════════════════════════════════════════════════════════════════════

class Result:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.tests: List[Tuple[str, str, str, str]] = []
        self.sample_statute: Optional[str] = None
        self.sample_article: Optional[str] = None
        self.repealed_title: Optional[str] = None
        self.repealed_article: Optional[str] = None

    def ok(self, group: str, name: str, msg: str = ""):
        self.passed += 1
        self.tests.append((group, name, "PASS", msg))

    def fail(self, group: str, name: str, msg: str = ""):
        self.failed += 1
        self.tests.append((group, name, "FAIL", msg))

    def skip(self, group: str, name: str, msg: str = ""):
        self.skipped += 1
        self.tests.append((group, name, "SKIP", msg))

    def summary(self) -> str:
        total = self.passed + self.failed + self.skipped
        lines = [
            "═" * 75,
            f"REZULTATI: {self.passed} PASS / {self.failed} FAIL / {self.skipped} SKIP (total {total})",
            "═" * 75,
        ]
        for group, name, status, msg in self.tests:
            icon = {"PASS": "✅", "FAIL": "❌", "SKIP": "⏭️"}.get(status, "❔")
            lines.append(f"{icon} [{group}] {name}")
            if status != "PASS" and msg:
                lines.append(f"      → {msg[:500]}")
        return "\n".join(lines)


RESULT = Result()


def _setup_client():
    from fastapi.testclient import TestClient
    return TestClient(APP, raise_server_exceptions=False)


# ═══════════════════════════════════════════════════════════════════════════
# TESTS
# ═══════════════════════════════════════════════════════════════════════════

def test_routes_present(client, prefix: str):
    group = "L0-routes"
    expected_paths = [
        f"{prefix}/titles",
        f"{prefix}/by-title",
        f"{prefix}/article",
        f"{prefix}/search",
        f"{prefix}/case-page",
    ]
    app_paths = _get_laws_paths_set()

    missing = [p for p in expected_paths if p not in app_paths]
    if missing:
        RESULT.fail(group, "rrugët e pritura ekzistojnë",
                    f"mungojnë: {missing} (gjendja: {sorted(app_paths)[:10]})")
    else:
        RESULT.ok(group, f"të gjitha rrugët laws ekzistojnë ({len(expected_paths)})")


def test_titles(client, prefix: str):
    group = "L1-titles"
    try:
        resp = client.get(f"{prefix}/titles")
    except Exception as e:
        RESULT.fail(group, "GET /titles", f"Exception: {e}")
        return

    if resp.status_code != 200:
        RESULT.fail(group, "GET /titles → 200",
                    f"status={resp.status_code}, body={resp.text[:200]}")
        return
    RESULT.ok(group, "GET /titles → 200")

    data = resp.json()
    for key in ["statutes", "case_law"]:
        if key not in data:
            RESULT.fail(group, f"response ka '{key}'", f"keys={list(data.keys())}")
            return
    RESULT.ok(group, "response ka 'statutes' + 'case_law'")

    n_statutes = len(data.get("statutes", []))
    n_caselaw = len(data.get("case_law", []))
    if n_statutes == 0:
        RESULT.fail(group, "statutes jo bosh", f"n={n_statutes}")
    else:
        RESULT.ok(group, f"statutes ka {n_statutes} hyrje")

    if n_caselaw == 0:
        RESULT.fail(group, "case_law jo bosh", f"n={n_caselaw}")
    else:
        RESULT.ok(group, f"case_law ka {n_caselaw} hyrje")

    for s in data.get("statutes", []):
        if "penal" in s.lower():
            RESULT.sample_statute = s
            break
    if not RESULT.sample_statute and data.get("statutes"):
        RESULT.sample_statute = data["statutes"][0]


def test_titles_no_junk(client, prefix: str):
    group = "L11-titles-no-junk"
    try:
        resp = client.get(f"{prefix}/titles")
    except Exception as e:
        RESULT.fail(group, "GET /titles", f"Exception: {e}")
        return

    if resp.status_code != 200:
        RESULT.fail(group, "GET /titles → 200", f"status={resp.status_code}")
        return

    data = resp.json()
    caselaw = data.get("case_law", [])
    junk_found = [
        t for t in caselaw
        if "PËRMBLEDHJE" in t.upper() or "PERMBLEDHJE" in t.upper()
    ]

    if junk_found:
        RESULT.fail(group, "case_law NUK ka 'PËRMBLEDHJE'",
                    f"gjetur {len(junk_found)}: {junk_found[:3]}")
    else:
        RESULT.ok(group, f"case_law pa junk ({len(caselaw)} hyrje)")


def test_titles_repealed(client, prefix: str):
    """V1.6 (L13): /titles kthen repealed_statutes me detaje."""
    group = "L13-titles-repealed"
    try:
        resp = client.get(f"{prefix}/titles")
    except Exception as e:
        RESULT.fail(group, "GET /titles", f"Exception: {e}")
        return

    if resp.status_code != 200:
        RESULT.fail(group, "GET /titles → 200", f"status={resp.status_code}")
        return

    data = resp.json()
    if "repealed_statutes" not in data:
        RESULT.fail(group, "response ka 'repealed_statutes'",
                    f"keys={list(data.keys())}")
        return
    RESULT.ok(group, "response ka 'repealed_statutes'")

    repealed = data.get("repealed_statutes", [])
    if not repealed:
        RESULT.fail(group, "repealed_statutes jo bosh",
                    "regjistri është bosh — a ka repealed_laws.json?")
        return
    RESULT.ok(group, f"repealed_statutes ka {len(repealed)} hyrje")

    # Kontrollo strukturën e detajeve
    first = repealed[0]
    for field in ["law_title", "repealed_by", "repealed_date", "warning"]:
        if field not in first:
            RESULT.fail(group, f"hyrja ka fushën '{field}'",
                        f"keys={list(first.keys())}")
            return
    RESULT.ok(group, "hyrja ka law_title, repealed_by, repealed_date, warning")

    # Ruaj për testet e ardhshme
    RESULT.repealed_title = first.get("law_title")


def test_titles_repealed_still_in_statutes(client, prefix: str):
    """V1.6 (L13b): Ligjet e shfuqizuara mbeten në 'statutes' (backward compat)."""
    group = "L13b-repealed-in-statutes"
    try:
        resp = client.get(f"{prefix}/titles")
    except Exception as e:
        RESULT.fail(group, "GET /titles", f"Exception: {e}")
        return

    if resp.status_code != 200:
        RESULT.fail(group, "GET /titles → 200", f"status={resp.status_code}")
        return

    data = resp.json()
    statutes = data.get("statutes", [])
    repealed = data.get("repealed_statutes", [])

    if not repealed:
        RESULT.skip(group, "kontroll backward compat", "pa repealed")
        return

    repealed_titles = {r.get("law_title") for r in repealed}
    for title in repealed_titles:
        if title not in statutes:
            RESULT.fail(group, "repealed gjendet edhe në statutes",
                        f"'{title[:60]}' mungon në statutes")
            return

    RESULT.ok(group, f"backward compat OK ({len(repealed_titles)} repealed mbeten në statutes)")


def test_by_title(client, prefix: str):
    group = "L2-by-title"
    if not RESULT.sample_statute:
        RESULT.skip(group, "GET /by-title", "no sample title")
        return

    try:
        resp = client.get(f"{prefix}/by-title",
                          params={"law_title": RESULT.sample_statute})
    except Exception as e:
        RESULT.fail(group, f"GET /by-title", f"Exception: {e}")
        return

    if resp.status_code != 200:
        RESULT.fail(group, "GET /by-title → 200",
                    f"status={resp.status_code}, body={resp.text[:300]}")
        return
    RESULT.ok(group, "GET /by-title → 200")

    data = resp.json()
    for k in ["law_title", "articles", "article_count"]:
        if k not in data:
            RESULT.fail(group, f"response ka '{k}'", f"keys={list(data.keys())}")
            return
    RESULT.ok(group, "response ka law_title, articles, article_count")

    # V208.2: is_repealed flag duhet të ekzistojë
    if "is_repealed" not in data:
        RESULT.fail(group, "response ka 'is_repealed' (V208.2)",
                    f"keys={list(data.keys())}")
    else:
        RESULT.ok(group, f"response ka 'is_repealed' = {data.get('is_repealed')}")

    n_arts = data.get("article_count", 0)
    if n_arts == 0:
        RESULT.fail(group, "article_count > 0", f"count={n_arts}")
    else:
        RESULT.ok(group, f"article_count = {n_arts}")

    canonical = data.get("law_title", "")
    if not canonical:
        RESULT.fail(group, "law_title jo bosh", "")
    else:
        RESULT.ok(group, f"canonical='{canonical[:60]}'")

    arts = data.get("articles", [])
    if arts:
        RESULT.sample_article = arts[0]


def test_by_title_repealed_warning(client, prefix: str):
    """V1.6 (L14): /by-title për ligj të shfuqizuar → warning."""
    group = "L14-by-title-repealed-warning"
    if not RESULT.repealed_title:
        RESULT.skip(group, "GET /by-title repealed", "pa repealed_title")
        return

    try:
        resp = client.get(f"{prefix}/by-title",
                          params={"law_title": RESULT.repealed_title})
    except Exception as e:
        RESULT.fail(group, "GET /by-title (repealed)", f"Exception: {e}")
        return

    if resp.status_code != 200:
        RESULT.fail(group, "GET /by-title → 200",
                    f"status={resp.status_code}, body={resp.text[:200]}")
        return
    RESULT.ok(group, "GET /by-title repealed → 200")

    data = resp.json()
    if data.get("is_repealed") is not True:
        RESULT.fail(group, "is_repealed=True",
                    f"is_repealed={data.get('is_repealed')}")
        return
    RESULT.ok(group, "is_repealed=True")

    if "repealed_info" not in data:
        RESULT.fail(group, "response ka 'repealed_info'",
                    f"keys={list(data.keys())}")
        return
    RESULT.ok(group, "response ka 'repealed_info'")

    info = data.get("repealed_info", {})
    for field in ["repealed_by", "repealed_date", "source"]:
        if not info.get(field):
            RESULT.fail(group, f"repealed_info.{field} jo bosh",
                        f"value={info.get(field)!r}")
            return
    RESULT.ok(group, "repealed_info ka details të plotë")

    warning = data.get("warning", "")
    if not warning or "⚠️" not in warning:
        RESULT.fail(group, "warning përmban '⚠️'", f"warning={warning[:100]!r}")
        return
    RESULT.ok(group, f"warning: {warning[:80]}...")

    # Ruaj article për testin e ardhshëm
    arts = data.get("articles", [])
    if arts:
        RESULT.repealed_article = arts[0]


def test_by_title_no_zero(client, prefix: str):
    group = "L10-by-title-no-zero"
    if not RESULT.sample_statute:
        RESULT.skip(group, "GET /by-title no-zero", "no sample title")
        return

    try:
        resp = client.get(f"{prefix}/by-title",
                          params={"law_title": RESULT.sample_statute})
    except Exception as e:
        RESULT.fail(group, "GET /by-title", f"Exception: {e}")
        return

    if resp.status_code != 200:
        RESULT.fail(group, "GET /by-title → 200", f"status={resp.status_code}")
        return

    data = resp.json()
    arts = data.get("articles", [])
    bad = [a for a in arts if str(a).strip() in ("0", "0.", "00")]

    if bad:
        RESULT.fail(group, "articles NUK përmban '0'", f"gjetur: {bad}")
    else:
        RESULT.ok(group, f"articles pa '0' ({len(arts)} nene të vlefshme)")


def test_article(client, prefix: str):
    group = "L3-article"
    if not RESULT.sample_statute or not RESULT.sample_article:
        RESULT.skip(group, "GET /article", "no sample title/article")
        return

    try:
        resp = client.get(
            f"{prefix}/article",
            params={
                "law_title": RESULT.sample_statute,
                "article_number": RESULT.sample_article,
            },
        )
    except Exception as e:
        RESULT.fail(group, "GET /article", f"Exception: {e}")
        return

    if resp.status_code != 200:
        RESULT.fail(group, "GET /article → 200",
                    f"status={resp.status_code}, body={resp.text[:200]}")
        return
    RESULT.ok(group, "GET /article → 200")

    data = resp.json()
    for k in ["law_title", "article_number", "text", "source_info"]:
        if k not in data:
            RESULT.fail(group, f"response ka '{k}'", f"keys={list(data.keys())}")
            return
    RESULT.ok(group, "response ka law_title, article_number, text, source_info")

    if "is_repealed" not in data:
        RESULT.fail(group, "response ka 'is_repealed' (V208.2)",
                    f"keys={list(data.keys())}")
    else:
        RESULT.ok(group, f"response ka 'is_repealed' = {data.get('is_repealed')}")

    conf = data.get("source_info", {}).get("confidence", {})
    level = conf.get("level")
    score = conf.get("score")
    if level == "HIGH" and score == 1.0:
        RESULT.fail(group, "confidence NUK është hardcoded HIGH/1.0",
                    f"level={level}, score={score} (fake!)")
    else:
        RESULT.ok(group, f"confidence real: level={level}, score={score}")

    page = data.get("page")
    if page == 1:
        page_avail = data.get("source_info", {}).get("page_available")
        if page_avail is False:
            RESULT.fail(group, "page=1 por page_available=False",
                        f"page={page}, page_available={page_avail}")
        else:
            RESULT.ok(group, f"page={page} (i besueshëm)")
    else:
        RESULT.ok(group, f"page={page} (jo fallback fake 1)")


def test_article_repealed_warning(client, prefix: str):
    """V1.6 (L15): /article për ligj të shfuqizuar → warning."""
    group = "L15-article-repealed-warning"
    if not RESULT.repealed_title or not RESULT.repealed_article:
        RESULT.skip(group, "GET /article repealed", "pa repealed info")
        return

    try:
        resp = client.get(
            f"{prefix}/article",
            params={
                "law_title": RESULT.repealed_title,
                "article_number": RESULT.repealed_article,
            },
        )
    except Exception as e:
        RESULT.fail(group, "GET /article (repealed)", f"Exception: {e}")
        return

    if resp.status_code != 200:
        RESULT.fail(group, "GET /article → 200",
                    f"status={resp.status_code}, body={resp.text[:200]}")
        return
    RESULT.ok(group, "GET /article repealed → 200")

    data = resp.json()
    if data.get("is_repealed") is not True:
        RESULT.fail(group, "is_repealed=True",
                    f"is_repealed={data.get('is_repealed')}")
        return
    RESULT.ok(group, "is_repealed=True")

    if "warning" not in data or "⚠️" not in data.get("warning", ""):
        RESULT.fail(group, "warning ka '⚠️'",
                    f"warning={data.get('warning', '')[:100]!r}")
        return
    RESULT.ok(group, "warning ka '⚠️'")

    if "repealed_info" not in data:
        RESULT.fail(group, "response ka 'repealed_info'", "")
        return
    RESULT.ok(group, "response ka 'repealed_info'")


def test_article_zero(client, prefix: str):
    group = "L12-article-zero"
    if not RESULT.sample_statute:
        RESULT.skip(group, "GET /article zero", "no sample title")
        return

    try:
        resp = client.get(
            f"{prefix}/article",
            params={
                "law_title": RESULT.sample_statute,
                "article_number": "0",
            },
        )
    except Exception as e:
        RESULT.fail(group, "GET /article (0)", f"Exception: {e}")
        return

    if resp.status_code == 404:
        RESULT.ok(group, "article_number=0 → 404 (jo frontmatter)")
    else:
        RESULT.fail(group, "article_number=0 → 404",
                    f"status={resp.status_code}, body={resp.text[:150]}")


def test_article_nonexistent(client, prefix: str):
    group = "L4-article-404"
    try:
        resp = client.get(
            f"{prefix}/article",
            params={"law_title": "Ligj Absurd 9999", "article_number": "99999"},
        )
    except Exception as e:
        RESULT.fail(group, "GET /article (gabim)", f"Exception: {e}")
        return

    if resp.status_code == 404:
        RESULT.ok(group, "ligj/nen inekzistent → 404 (jo shpikje)")
    elif resp.status_code == 500:
        RESULT.fail(group, "ligj inekzistent → 500", f"body={resp.text[:200]}")
    else:
        RESULT.fail(group, "ligj inekzistent → 404",
                    f"status={resp.status_code}")


def test_search(client, prefix: str):
    group = "L5-search"
    try:
        resp = client.get(f"{prefix}/search", params={"q": "kodi penal", "limit": 5})
    except Exception as e:
        RESULT.fail(group, "GET /search", f"Exception: {e}")
        return

    if resp.status_code != 200:
        RESULT.fail(group, "GET /search → 200",
                    f"status={resp.status_code}, body={resp.text[:200]}")
        return
    RESULT.ok(group, "GET /search → 200")

    data = resp.json()
    if not isinstance(data, list):
        RESULT.fail(group, "response është list", f"type={type(data).__name__}")
        return
    RESULT.ok(group, f"response është list ({len(data)} results)")


def test_search_empty(client, prefix: str):
    group = "L6-search-empty"
    try:
        resp = client.get(f"{prefix}/search", params={"q": "", "limit": 5})
    except Exception as e:
        RESULT.fail(group, "GET /search q=''", f"Exception: {e}")
        return

    if resp.status_code == 400:
        RESULT.ok(group, "q bosh → 400 (validation)")
    else:
        RESULT.fail(group, "q bosh → 400", f"status={resp.status_code}")


def test_case_page(client, prefix: str):
    group = "L7-case-page"
    try:
        resp = client.get(
            f"{prefix}/case-page",
            params={"law_title": "Case_Law Absurd 9999"},
        )
    except Exception as e:
        RESULT.fail(group, "GET /case-page", f"Exception: {e}")
        return

    if resp.status_code != 200:
        RESULT.fail(group, "GET /case-page → 200", f"status={resp.status_code}")
        return
    RESULT.ok(group, "GET /case-page → 200")

    data = resp.json()
    if "found" not in data:
        RESULT.fail(group, "response ka 'found'", f"keys={list(data.keys())}")
        return
    RESULT.ok(group, f"found={data.get('found')}")

    if data.get("found") is False and data.get("page") is not None:
        RESULT.fail(group, "found=False → page=None",
                    f"found={data.get('found')}, page={data.get('page')}")
    else:
        RESULT.ok(group, "found/page konsistentë")


def test_pdf_with_auth(client, prefix: str):
    group = "L8-pdf-auth"
    try:
        resp = client.get(f"{prefix}/pdf/kodi_penal.pdf", follow_redirects=False)
    except Exception as e:
        RESULT.fail(group, "GET /pdf me auth", f"Exception: {e}")
        return

    if resp.status_code in (200, 404):
        RESULT.ok(group, f"me auth → {resp.status_code} (jo 401, jo 500)")
        return

    if resp.status_code == 500:
        tb_text = _debug_pdf_500(prefix)
        RESULT.fail(
            group, "me auth → 500 (server error)",
            f"body='{resp.text[:100]}' | traceback: {tb_text[:600]}",
        )
        return

    if resp.status_code == 401:
        RESULT.fail(group, "me auth → jo 401",
                    "auth override dështoi?")
        return

    RESULT.fail(group, f"me auth → {resp.status_code} (i papritur)",
                f"body={resp.text[:200]}")


def _debug_pdf_500(prefix: str) -> str:
    from fastapi.testclient import TestClient
    saved = dict(APP.dependency_overrides)
    try:
        strict_client = TestClient(APP, raise_server_exceptions=True)
        try:
            strict_client.get(f"{prefix}/pdf/kodi_penal.pdf")
            return "(no exception — status jo 500)"
        except Exception as e:
            tb = traceback.format_exc()
            return f"{type(e).__name__}: {e}\n{tb[-800:]}"
    finally:
        APP.dependency_overrides = saved


def test_pdf_without_auth(prefix: str):
    group = "L9-pdf-no-auth"
    from fastapi.testclient import TestClient
    try:
        saved = dict(APP.dependency_overrides)
        APP.dependency_overrides.clear()
        raw_client = TestClient(APP, raise_server_exceptions=False)
        resp = raw_client.get(f"{prefix}/pdf/kodi_penal.pdf", follow_redirects=False)
        APP.dependency_overrides.update(saved)
    except Exception as e:
        RESULT.fail(group, "GET /pdf pa auth", f"Exception: {e}")
        return

    if resp.status_code in (401, 403):
        RESULT.ok(group, f"pa auth → {resp.status_code} (siguri OK)")
    else:
        RESULT.fail(group, "pa auth → 401/403",
                    f"status={resp.status_code} (RREZIK SIGURIE!)")


# ═══════════════════════════════════════════════════════════════════════════
# RUNNER
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("═" * 75)
    print("LIVE ENDPOINT TESTS V1.6 — Biblioteka Ligjore + Repeals")
    print("═" * 75)
    print()

    if not _build_test_app():
        print(f"❌ {APP_ERROR}")
        sys.exit(1)
    print(f"✅ Test app: {APP_SOURCE}")
    print(f"✅ Laws prefix: {LAWS_PREFIX}")

    routes = _get_openapi_paths()
    print(f"✅ Rrugë laws të montuara: {len(routes)}")
    for path, methods_str in routes:
        print(f"   • {methods_str:22s} {path}")
    print()

    try:
        client = _setup_client()
        print("✅ TestClient + auth override gati\n")
    except Exception as e:
        print(f"❌ Client setup failed: {e}")
        print(traceback.format_exc())
        sys.exit(1)

    print("─" * 75)
    print("TESTET")
    print("─" * 75)

    test_routes_present(client, LAWS_PREFIX)
    test_titles(client, LAWS_PREFIX)
    test_titles_no_junk(client, LAWS_PREFIX)
    test_titles_repealed(client, LAWS_PREFIX)
    test_titles_repealed_still_in_statutes(client, LAWS_PREFIX)
    test_by_title(client, LAWS_PREFIX)
    test_by_title_repealed_warning(client, LAWS_PREFIX)
    test_by_title_no_zero(client, LAWS_PREFIX)
    test_article(client, LAWS_PREFIX)
    test_article_repealed_warning(client, LAWS_PREFIX)
    test_article_zero(client, LAWS_PREFIX)
    test_article_nonexistent(client, LAWS_PREFIX)
    test_search(client, LAWS_PREFIX)
    test_search_empty(client, LAWS_PREFIX)
    test_case_page(client, LAWS_PREFIX)
    test_pdf_with_auth(client, LAWS_PREFIX)
    test_pdf_without_auth(LAWS_PREFIX)

    print()
    print(RESULT.summary())

    sys.exit(0 if RESULT.failed == 0 else 1)


if __name__ == "__main__":
    main()