"""Build assets/data/chatbot.json, the answer index for the site assistant (js/chatbot.js).

Usage (from the repository root):  python tools/build_chatbot.py

The assistant only ever repeats what this file holds, and this file only holds
what is already published on the site: the FAQPage answers and each page's
meta description, taken from the pages listed in sitemap.xml, plus the reel
captions Ryan has reviewed in assets/data/reel_answers.json. To change an
answer, change the page and rebuild. Standard library only.
"""
import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "data" / "chatbot.json"
REELS = ROOT / "assets" / "data" / "reel_answers.json"
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December")
LD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
TAG = re.compile(r"<[^>]+>")


# Piju's menu: subject, then activity, then question. CA subjects first; income tax and GST separate.
# A question goes to the first activity whose pattern matches, so a new FAQ on a page appears by itself.
MENU = [
    ("income-tax", "Income tax", [
        ("act", "Income-tax Act, 2025", r"$^"),
        ("ais", "AIS and Form 26AS", r"\bAIS\b|26AS"),
        ("notices", "Notices and appeals", r"notice|intimation|defective"),
        ("tds", "TDS and TCS", r"\bTDS\b|\bTCS\b"),
        ("planning", "Regime and advance tax", r"regime|advance tax|no tax"),
        ("gains", "Capital gains and gifts", r"house|shares|gift"),
        ("returns", "Returns and due dates", r".")]),
    ("gst", "GST", [
        ("registration", "Registration", r"(?<!after my )registration|REG-|rule 14B|e-commerce seller|cancellation"),
        ("returns", "Returns and annual return", r"GSTR-3B be|GSTR-9|QRMP|return|late fee|ARQP|late GST"),
        ("litigation", "Notices and litigation", r"notice|DRC|ASMT|appeal|penalt|arrest"),
        ("itc", "ITC and reconciliation", r"\bITC\b|GSTR-2|GSTR-1|\bIMS\b|Invoice Management|reconciliation"),
        ("refunds", "Refunds and exports", r"refund|inverted|export"),
        ("tds", "GST TDS on scrap", r"\bTDS\b|scrap"),
        ("eway", "E-way bills and e-invoices", r"e-way|e-invoic"),
        ("changes", "Circulars and latest changes", r"changes? (in|applicable)|What changes|discount|credit note"),
        ("other", "Other GST questions", r".")]),
    ("nri", "NRI", [
        ("status", "Residential status", r"RNOR|Who is|Who qualifies|non-resident \\(NRI\\)"),
        ("returns", "Filing returns", r"file an income tax return"),
        ("property", "Property", r"property|buyer|\\bTAN\\b"),
        ("banking", "NRE, NRO and returning to India", r"."),
        ("dtaa", "DTAA", r"$^"),
        ("investments", "Investments", r"$^"),
        ("notices", "Notices", r"$^")]),
    ("audit", "Audit", [
        ("forensic", "Forensic audit", r"forensic"),
        ("audit", "Statutory, tax and internal audit", r".")]),
    ("society", "Housing society", [("all", "Housing society", r".")]),
    ("accounts", "Accounts and CFO", [
        ("cfo", "Fractional CFO", r"CFO"),
        ("models", "Financial models", r"model|DSCR"),
        ("books", "Accounts and bookkeeping", r".")]),
    ("business", "Starting a business", [("all", "Starting a business", r".")]),
    ("foreign", "Foreign and international", [
        ("india", "Foreign companies in India", r"foreign|subsidiary|Indian compan"),
        ("abroad", "Clients outside India", r".")]),
    ("tools", "Due dates and calculators", [("all", "Due dates and calculators", r"$^")]),
    ("firm", "Office and contact", [("all", "Office and contact", r".")]),
    ("tech", "AI and automation", [
        ("automation", "Finance automation and AI", r"AI\b|Python|automation"),
        ("script", "Google Apps Script", r"Apps Script|script|Google"),
        ("digital", "Digital transformation", r".")]),
    ("web", "Web design", [("all", "Web design", r".")]),
]
MENU_LINKS = {
    "gst/changes": [["All GST changes by date", "/services/gst-updates/#dated-title"],
                    ["CBIC Circulars 257 to 266", "/services/gst-updates/#circulars-title"]],
    "gst/returns": [["Due dates: compliance calendar", "/compliance-calendar/"]],
    "income-tax/returns": [["Due dates: compliance calendar", "/compliance-calendar/"]],
    "income-tax/planning": [["Tax calculators", "/tax-tools/"]],
    "tools/all": [["Compliance calendar", "/compliance-calendar/"], ["Tax calculators", "/tax-tools/"]],
}
PATH_AREA = {"gst": "gst", "gst-reconciliation": "gst", "gst-notices": "gst", "gstr-9-annual-return": "gst", "gst-updates": "gst",
             "income-tax": "income-tax", "income-tax-act-2025": "income-tax", "tds-tcs": "income-tax", "itr-returns-refunds": "income-tax", "ais-26as-reconciliation": "income-tax", "nri-taxation": "nri", "nri-tax-questions": "nri",
             "audit-assurance": "audit", "forensic-audit": "audit", "housing-society": "society",
             "accounts-bookkeeping": "accounts", "fractional-cfo": "accounts", "financial-modelling": "accounts",
             "foreign-business": "foreign", "international": "foreign", "ca-borivali-west": "firm",
             "finance-automation": "tech", "google-apps-script": "tech", "digital-transformation": "tech", "web-design": "web"}


def menu_area(path, anchor, q):
    slug = path.strip("/").split("/")[-1]
    if slug in PATH_AREA:
        return PATH_AREA[slug]
    if slug == "faq":
        if re.match(r"nri|nre", anchor):
            return "nri"
        if anchor == "what-is-fractional-cfo":
            return "accounts"
        if anchor in ("proprietorship-llp-company", "udyam-45-day-rule"):
            return "business"
        if re.search(r"GST|e-invoice|e-commerce|show-cause|ARQP", q):
            return "gst"
        return "income-tax"
    if slug == "tax-tools" and re.search(r"NRI|buyer", q):
        return "nri"
    if re.search(r"GST", q):
        return "gst"
    return "income-tax"


def menu_place(path, anchor, q):
    group = re.match(r"nri-(status|returns|property|banking|dtaa|investments|notices)-", anchor)
    tax = re.match(r"it-(act|tds|returns)-", anchor)
    if tax:
        return "income-tax/" + tax.group(1)
    if group:  # the NRI questions page groups its own answers
        return "nri/" + group.group(1)
    area = menu_area(path, anchor, q)
    for a, _, subs in MENU:
        if a == area:
            for sub, _, pattern in subs:
                if re.search(pattern, q, re.I if area not in ("income-tax", "nri") else 0):
                    return f"{a}/{sub}"
    return None


def menu_tree(entries):
    used = {e["m"] for e in entries if e.get("m")}
    tree = []
    for a, label, subs in MENU:
        items = [{"id": f"{a}/{s}", "label": l, "links": MENU_LINKS.get(f"{a}/{s}", [])}
                 for s, l, _ in subs if f"{a}/{s}" in used or f"{a}/{s}" in MENU_LINKS]
        if items:
            tree.append({"id": a, "label": label, "subs": items})
    return tree


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


def reel_entries():
    """Reviewed reel captions, each stating its date so that older law is not read as current."""
    if not REELS.exists():
        return []
    out = []
    for r in json.loads(REELS.read_text(encoding="utf8")).get("reels", []):
        caption = clean(r.get("caption", ""))
        if r.get("hide") or not caption:
            continue
        y, m, d = (int(x) for x in r["date"].split("-"))
        posted = f"{d} {MONTHS[m - 1]} {y}"
        out.append({"q": caption[:120], "a": f"From a reel posted on {posted}: {caption}", "u": r["url"],
                    "t": f"reel posted on {posted}", "k": "reel", "d": r["date"]})
    return out


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
            entry = {"q": q, "a": a, "u": path + (f"#{anchor}" if anchor else ""), "t": title, "k": kind}
            if kind != "local":
                entry["m"] = menu_place(path, anchor or "", q)
            entries.append(entry)
        desc = first(r'<meta name="description" content="([^"]*)"', source)
        if desc and path not in ("/", "/faq/"):
            entries.append({"q": title, "a": desc, "u": path, "t": title, "k": "summary"})
    entries += reel_entries()
    if len(entries) < 100:
        raise SystemExit(f"Only {len(entries)} entries found; check the page markup")
    OUT.write_text(json.dumps({"menu": menu_tree(entries), "entries": entries}, ensure_ascii=False, separators=(",", ":")) + "\n",
                   encoding="utf8")
    print(f"{OUT.relative_to(ROOT)}: {len(entries)} entries from {len(paths)} pages")


if __name__ == "__main__":
    main()
