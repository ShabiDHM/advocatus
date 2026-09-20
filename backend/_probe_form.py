# -*- coding: utf-8 -*-
"""Zbulon formen e kerkimit dhe si funksionon paginimi."""
import re
from bs4 import BeautifulSoup

with open("_page_dump.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

print("=" * 70)
print("1. FORMAT")
print("=" * 70)
for form in soup.find_all("form"):
    action = form.get("action", "")
    method = form.get("method", "get")
    fid = form.get("id", "")
    print(f"  form id='{fid}' method={method} action='{action[:80]}'")
    for inp in form.find_all(["input", "select"]):
        name = inp.get("name", "")
        itype = inp.get("type", "select" if inp.name == "select" else "?")
        value = inp.get("value", "")
        if name:
            print(f"    input name='{name}' type={itype} value='{value[:30]}'")

print("\n" + "=" * 70)
print("2. CUSTOM POST TYPES ne wp-json")
print("=" * 70)
# Kerko per custom post type deklarime
for m in re.finditer(r'wp-json/wp/v2/([a-z_\-]+)', html):
    print(f"  /wp-json/wp/v2/{m.group(1)}")

print("\n" + "=" * 70)
print("3. KERKO 'displayResults' - konteksti rreth")
print("=" * 70)
idx = html.find("displayResults")
if idx >= 0:
    print(html[max(0, idx-500):idx+500])

print("\n" + "=" * 70)
print("4. KERKO 'page' ose 'paged' si input/element")
print("=" * 70)
for elem in soup.find_all(["input", "a", "button"]):
    name = elem.get("name", "")
    href = elem.get("href", "")
    text = elem.get_text(strip=True) if elem.name != "input" else ""
    if "page" in name.lower() or "page" in href.lower() or text in ("2", "3", "4"):
        print(f"  <{elem.name}> name='{name}' href='{href[:60]}' text='{text[:20]}'")