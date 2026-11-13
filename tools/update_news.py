"""Rebuild the News page from tools/news.json.

Usage (from the repository root):  python tools/update_news.py
Rewrites the part of news/index.html between the NEWS markers, the
"Status as on" line, and dateModified in the page markup.
Standard library only.
"""
import json, os, re, sys, datetime as dt
from html import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "news", "index.html")
DATA = os.path.join(ROOT, "tools", "news.json")


def human(d):
    return "%d %s" % (d.day, d.strftime("%B %Y"))


def short(d):
    return "%d %s" % (d.day, d.strftime("%b %Y"))


def build(data):
    acts = data["acts"]
    items = data["items"]
    for it in items:
        if it["act"] not in acts:
            sys.exit("Unknown act %r in item %r" % (it["act"], it["title"]))
        it["_d"] = dt.date.fromisoformat(it["date"])
    out = []
    for key, name in acts.items():
        rows = sorted((i for i in items if i["act"] == key), key=lambda i: i["_d"], reverse=True)
        out.append('<section class="section%s" aria-labelledby="news-%s">' % (" section--alt" if len(out) % 2 else "", key))
        out.append('  <div class="container">')
        out.append('    <h2 id="news-%s" class="reveal">%s</h2>' % (key, escape(name)))
        if not rows:
            out.append('    <p class="muted">No changes recorded yet. Changes will be added here as they are notified.</p>')
        else:
            out.append('    <div class="table-wrap reveal"><table class="news-table">')
            out.append('      <thead><tr><th scope="col" class="num">Date</th><th scope="col">Change</th><th scope="col">Reference</th><th scope="col">In force from</th></tr></thead>')
            out.append('      <tbody>')
            for r in rows:
                title = escape(r["title"])
                if r.get("link"):
                    title = '<a href="../%s">%s</a>' % (escape(r["link"], quote=True), title)
                out.append('        <tr><td class="num" data-label="Date">%s</td><td data-label="Change">%s<br><span class="muted">%s</span></td><td data-label="Reference">%s</td><td data-label="In force from">%s</td></tr>'
                           % (short(r["_d"]), title, escape(r["summary"]), escape(r["ref"]), escape(r["effective"])))
            out.append('      </tbody>')
            out.append('    </table></div>')
        out.append('  </div>')
        out.append('</section>')
    return "\n".join(out)


def main():
    data = json.load(open(DATA, encoding="utf-8"))
    lu = dt.date.fromisoformat(data["last_updated"])
    page = open(PAGE, encoding="utf-8").read()
    block = build(data)
    page, n = re.subn(r"(<!-- NEWS:START -->).*?(<!-- NEWS:END -->)",
                      lambda m: m.group(1) + "\n" + block + "\n" + m.group(2), page, flags=re.S)
    if n != 1:
        sys.exit("NEWS markers not found in news/index.html")
    page = re.sub(r"Status as on [0-9]{1,2} [A-Z][a-z]+ [0-9]{4}\.", "Status as on %s." % human(lu), page)
    page = re.sub(r'"dateModified":"[0-9-]+"', '"dateModified":"%s"' % lu.isoformat(), page)
    open(PAGE, "w", encoding="utf-8", newline="\n").write(page)
    print("news/index.html rebuilt: %d items, status as on %s" % (len(data["items"]), human(lu)))


if __name__ == "__main__":
    main()
