"""Build assets/data/chatbot.json, the answer index for the site assistant (js/chatbot.js).

Usage (from the repository root):  python tools/build_chatbot.py

The assistant only ever repeats what this file holds, and this file only holds
what is already published on the site: the FAQPage answers and each page's
meta description, taken from the pages listed in sitemap.xml. To change an
answer, change the page and rebuild. Standard library only.
"""
import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "data" / "chatbot.json"
LD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
TAG = re.compile(r"<[^>]+>")


def clean(text):
    return re.sub(r"\s+", " ", html.unescape(TAG.sub("", text))).strip()


def first(pattern, source):
    m = re.search(pattern, source, re.S)
    return clean(m.group(1)) if m else ""


def faq_items(source):
    for block in LD.findall(source):
        data = json.loads(block)
        nodes = data if isinstance(data, list) else data.get("@graph", [data])
        for node in nodes:
            if node.get("@type") == "FAQPage":
                yield from node["mainEntity"]


def main():
    sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf8")
    paths = [urlparse(u).path for u in re.findall(r"<loc>(.*?)</loc>", sitemap)]
    # The FAQ page goes first, so a repeated question keeps its direct link there.
    paths.sort(key=lambda p: p != "/faq/")
    entries, seen = [], set()
    for path in paths:
        file = ROOT / path.lstrip("/") / "index.html"
        if not file.exists():
            raise SystemExit(f"{path} is in sitemap.xml but {file} does not exist")
        source = file.read_text(encoding="utf8")
        title = first(r"<h1[^>]*>(.*?)</h1>", source)
        anchors = {clean(q): i for i, q in re.findall(
            r'<details id="([^"]+)">\s*<summary>(.*?)</summary>', source, re.S)}
        kind = "faq" if path == "/faq/" else "local" if re.match(r"/(ca-in-|areas-served)", path) else "page"
        for item in faq_items(source):
            q, a = clean(item["name"]), clean(item["acceptedAnswer"]["text"])
            if q.lower() in seen:
                continue
            seen.add(q.lower())
            anchor = anchors.get(q)
            entries.append({"q": q, "a": a, "u": path + (f"#{anchor}" if anchor else ""),
                            "t": title, "k": kind})
        desc = first(r'<meta name="description" content="([^"]*)"', source)
        if desc and path not in ("/", "/faq/"):
            entries.append({"q": title, "a": desc, "u": path, "t": title, "k": "summary"})
    if len(entries) < 100:
        raise SystemExit(f"Only {len(entries)} entries found; check the page markup")
    OUT.write_text(json.dumps({"entries": entries}, ensure_ascii=False, separators=(",", ":")) + "\n",
                   encoding="utf8")
    print(f"{OUT.relative_to(ROOT)}: {len(entries)} entries from {len(paths)} pages")


if __name__ == "__main__":
    main()
