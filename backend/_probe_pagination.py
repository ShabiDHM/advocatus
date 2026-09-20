# -*- coding: utf-8 -*-
"""Zbulon si funksionon paginimi i faqes Supreme."""
import requests
import re
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
BASE = "https://supreme.gjyqesori-rks.org/publikimet/aktgjykimet/"


def main():
    print("=" * 70)
    print("PROBE PAGINATION")
    print("=" * 70)

    r = requests.get(BASE, headers=HEADERS, timeout=30)
    html = r.text

    # Ruaj HTML per inspektim
    with open("_page_dump.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML ruajtur: _page_dump.html ({len(html)} chars)")

    print("\n" + "=" * 70)
    print("1. LINK rel=next/prev ne <head>")
    print("=" * 70)
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.find_all("link", rel=True):
        rel = " ".join(link.get("rel", []))
        if "next" in rel or "prev" in rel:
            print(f"  rel={rel}  href={link.get('href', '')}")

    print("\n" + "=" * 70)
    print("2. TABELA - atributet (data-*, id, class)")
    print("=" * 70)
    tables = soup.find_all("table")
    for i, t in enumerate(tables):
        print(f"  Table {i}: id='{t.get('id', '')}' class='{t.get('class', [])}'")
        # Data attributes
        data_attrs = {k: v for k, v in t.attrs.items() if k.startswith("data-")}
        if data_attrs:
            print(f"    data-*: {data_attrs}")

    print("\n" + "=" * 70)
    print("3. SCRIPT blocks - kerkojme 'ajax', 'api', 'fetch', 'paged'")
    print("=" * 70)
    scripts = soup.find_all("script")
    keywords = ["ajax", "paged", "page=", "api/", "fetch(", "wp-json", "admin-ajax"]
    for s in scripts:
        src = s.get("src", "")
        inline = s.string or ""
        for kw in keywords:
            if kw.lower() in src.lower() or kw.lower() in inline.lower():
                print(f"  SCRIPT (src='{src[:80]}'):")
                # Nxjerr snippet-in rreth keywords
                if inline:
                    idx = inline.lower().find(kw.lower())
                    if idx >= 0:
                        snippet = inline[max(0, idx-100):idx+200]
                        print(f"    ...{snippet}...")
                break

    print("\n" + "=" * 70)
    print("4. Kerko 'wp-json' ose 'admin-ajax.php' ne HTML")
    print("=" * 70)
    for pattern in [r'wp-json[^\s"\']*', r'admin-ajax\.php[^\s"\']*', r'/api/[^\s"\']*']:
        matches = re.findall(pattern, html)
        unique = list(set(matches))[:5]
        for m in unique:
            print(f"  {m}")

    print("\n" + "=" * 70)
    print("5. Kerko 'verdicts' (folder i PDF-ve) ne HTML")
    print("=" * 70)
    verdicts = re.findall(r'[/\w\-\.]*verdicts[/\w\-\.]*\.pdf', html)
    unique_verdicts = list(set(verdicts))[:5]
    print(f"  Gjetur {len(verdicts)} refs unike ({len(set(verdicts))})")
    for v in unique_verdicts:
        print(f"  {v[:100]}")

    print("\n" + "=" * 70)
    print("6. Kerko numra te faqeve (1, 2, 3...) brenda HTML")
    print("=" * 70)
    # Kerko per nje element qe permban '2' si text
    for a in soup.find_all("a"):
        text = a.get_text(strip=True)
        if text in ("2", "3", "Next", "Tjetra", "»", "→"):
            href = a.get("href", "")
            print(f"  text='{text}'  href='{href[:80]}'")

    print("\n" + "=" * 70)
    print("7. Kerko 'datatable', 'tabulator', 'grid' ne CSS/JS")
    print("=" * 70)
    for kw in ["datatable", "tabulator", "grid.js", "data-table", "verdict-table"]:
        if kw in html.lower():
            print(f"  Gjetur: '{kw}'")
            idx = html.lower().find(kw.lower())
            print(f"    Context: ...{html[max(0,idx-80):idx+150]}...")


if __name__ == "__main__":
    main()