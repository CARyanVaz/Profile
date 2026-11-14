"""Checks run on every push and pull request (see .github/workflows/site-checks.yml).

Usage (from the repository root):  python tools/check_site.py
Fails (exit 1) on: broken internal links, JSON-LD that does not parse, ICAI-banned
wording, ICAI membership or firm registration number on a page, sitemap entries
without lastmod or pointing to a missing page.
Warns (does not fail) on: pages missing from sitemap.xml.
Standard library only.
"""
import json, os, re, sys
from html.parser import HTMLParser
from urllib.parse import urlparse, unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "vazassociates.in"
SKIP_FILES = re.compile(r"^google[0-9a-f]+\.html$")

# Wording the ICAI Code of Ethics rules out on the site (see the project SOP, section 3).
BANNED = [
    (re.compile(r"\bbest\b(?!\s+judg)", re.I), "superlative 'best'"),
    (re.compile(r"\bpremier\b", re.I), "superlative 'premier'"),
    (re.compile(r"\b(a|the)\s+leading\b", re.I), "superlative 'leading'"),
    (re.compile(r"\bno\.?\s*1\b|#1\b|number one", re.I), "superlative 'number one'"),
    (re.compile(r"\btestimonials?\b", re.I), "testimonial"),
    (re.compile(r"\b(review us|leave (us )?a review|rate us)\b", re.I), "review request"),
    (re.compile(r"\b(our|consultation|audit|retainer)\s+fees?\b|(?<!late )(?<!filing )\bfees?\s+(start|from|of\s+rs|of\s+₹)|\b(our|transparent|affordable)\s+pricing\b|\bstarting\s+(at|from)\s+(rs|₹)", re.I), "fees or price"),
    (re.compile(r"priceRange", re.I), "priceRange in markup"),
]
BANNED_NUMBERS = [(re.compile(r"\b110356\b"), "ICAI membership number"),
                  (re.compile(r"\b025088S\b", re.I), "firm registration number")]


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links, self.ldjson, self.text = [], [], []
        self._in_ld = self._skip = False
        self._buf = []
        self.noindex = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "script" and a.get("type") == "application/ld+json":
            self._in_ld, self._buf = True, []
        elif tag in ("script", "style"):
            self._skip = True
        if tag in ("a", "link") and a.get("href"):
            if tag == "a" or a.get("rel") in ("canonical", "stylesheet", "icon", "manifest"):
                self.links.append(a["href"])
        if tag in ("img", "script", "source") and a.get("src"):
            self.links.append(a["src"])
        if tag == "meta" and a.get("name") == "robots" and "noindex" in (a.get("content") or ""):
            self.noindex = True
        if tag == "meta" and a.get("name") in ("description",) and a.get("content"):
            self.text.append(a["content"])

    def handle_endtag(self, tag):
        if tag == "script" and self._in_ld:
            self.ldjson.append("".join(self._buf))
            self._in_ld = False
        elif tag in ("script", "style"):
            self._skip = False

    def handle_data(self, data):
        if self._in_ld:
            self._buf.append(data)
        elif not self._skip:
            self.text.append(data)


def target_exists(path):
    p = os.path.join(ROOT, unquote(path).lstrip("/"))
    if path.endswith("/"):
        return os.path.isfile(os.path.join(p, "index.html"))
    return os.path.isfile(p) or os.path.isfile(p + ".html") or os.path.isfile(os.path.join(p, "index.html"))


def resolve(href, page_rel):
    u = urlparse(href)
    if u.scheme in ("mailto", "tel", "javascript", "data", "whatsapp", "sms"):
        return None
    if u.scheme in ("http", "https"):
        if u.netloc.lower().removeprefix("www.") != SITE:
            return None
        return u.path or "/"
    if not u.path:
        return None
    if u.path.startswith("/"):
        return u.path
    base = os.path.dirname("/" + page_rel)
    return os.path.normpath(os.path.join(base, u.path)) + ("/" if u.path.endswith("/") else "")


def page_url(rel):
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    return "/" + rel


def main():
    errors, warnings, pages = [], [], {}
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if not x.startswith(".") and x != "node_modules"]
        for f in files:
            if f.endswith(".html") and not SKIP_FILES.match(f):
                rel = os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, "/")
                p = Page()
                with open(os.path.join(d, f), encoding="utf-8") as fh:
                    p.feed(fh.read())
                pages[rel] = p

    for rel, p in sorted(pages.items()):
        for href in p.links:
            path = resolve(href.strip(), rel)
            if path and not target_exists(path):
                errors.append(f"{rel}: broken link {href}")
        for i, block in enumerate(p.ldjson, 1):
            try:
                json.loads(block)
            except ValueError as e:
                errors.append(f"{rel}: JSON-LD block {i} does not parse ({e})")
        text = " ".join(p.text) + " " + " ".join(p.ldjson)
        for rx, why in BANNED + BANNED_NUMBERS:
            for m in rx.finditer(text):
                before = text[max(0, m.start() - 60):m.start()].lower()
                if re.search(r"\b(no|not|without|restrictions? on|rules? on|bans?)\b", before):
                    continue  # the rule itself being described, e.g. "restrictions on testimonials"
                s = max(0, m.start() - 40)
                errors.append(f"{rel}: {why}: ...{' '.join(text[s:m.end() + 40].split())}...")
                break

    sm = os.path.join(ROOT, "sitemap.xml")
    listed = set()
    if os.path.isfile(sm):
        xml = open(sm, encoding="utf-8").read()
        for block in re.findall(r"<url>(.*?)</url>", xml, re.S):
            loc = re.search(r"<loc>(.*?)</loc>", block)
            if not loc:
                errors.append("sitemap.xml: <url> without <loc>")
                continue
            path = urlparse(loc.group(1).strip()).path or "/"
            listed.add(path)
            if not re.search(r"<lastmod>\d{4}-\d{2}-\d{2}</lastmod>", block):
                errors.append(f"sitemap.xml: {path} has no lastmod")
            if not target_exists(path):
                errors.append(f"sitemap.xml: {path} points to a missing page")
    for rel, p in pages.items():
        u = page_url(rel)
        if not p.noindex and rel != "404.html" and u not in listed:
            warnings.append(f"{rel}: not in sitemap.xml")

    for w in warnings:
        print("WARNING", w)
    for e in errors:
        print("ERROR", e)
    print(f"Checked {len(pages)} pages: {len(errors)} errors, {len(warnings)} warnings.")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
