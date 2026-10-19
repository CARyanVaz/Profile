"""Rebuild the compliance calendar tables from tools/calendar.json.

Usage (from the repository root):  python tools/update_calendar.py
Rewrites the parts of compliance-calendar/index.html between the
CAL markers: the month dropdown, the month tables, and the 'Last updated' date.
Standard library only.
"""
import json, os, re, sys, datetime as dt
from html import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "compliance-calendar", "index.html")
DATA = os.path.join(ROOT, "tools", "calendar.json")

def human(d):
    return "%d %s" % (d.day, d.strftime("%B %Y"))

def main():
    data = json.load(open(DATA, encoding="utf-8"))
    acts = data["acts"]
    rows = []
    for r in data["rows"]:
        if r["act"] not in acts:
            sys.exit("Unknown act %r in row %r" % (r["act"], r))
        rows.append((dt.date.fromisoformat(r["date"]), r))
    order = list(acts)
    rows.sort(key=lambda x: (x[0], order.index(x[1]["act"])))
    months = []
    for d, _ in rows:
        if (d.year, d.month) not in months:
            months.append((d.year, d.month))
    first = rows[0][0] if rows else None

    mopts = "\n".join('          <option value="%d-%02d">%s</option>' % (y, m, dt.date(y, m, 1).strftime("%B %Y")) for y, m in months)
    secs = []
    for y, m in months:
        trs = []
        for d, r in rows:
            if (d.year, d.month) != (y, m):
                continue
            trs.append('          <tr data-act="%s" data-date="%s"><td class="num"><time datetime="%s">%d %s %d</time></td>'
                       '<td><span class="act-tag act-%s">%s</span></td><td>%s</td><td class="muted">%s</td></tr>'
                       % (r["act"], d.isoformat(), d.isoformat(), d.day, d.strftime("%b"), d.year,
                          r["act"], escape(acts[r["act"]]), escape(r["text"]), escape(r.get("who", ""))))
        label = dt.date(y, m, 1).strftime("%B %Y")
        secs.append('''    <section class="cal-month" data-month="%d-%02d" aria-labelledby="m%d%02d">
      <h2 id="m%d%02d" class="cal-month-title">%s</h2>
      <div class="table-wrap">
        <table>
          <thead><tr><th scope="col" class="num">Due date</th><th scope="col">Act</th><th scope="col">Compliance</th><th scope="col">Who it applies to</th></tr></thead>
          <tbody>
%s
          </tbody>
        </table>
      </div>
    </section>''' % (y, m, y, m, y, m, label, "\n".join(trs)))

    s = open(PAGE, encoding="utf-8").read()
    def put(name, content):
        global_s = re.compile(r"(<!-- CAL:%s:START -->)(.*?)(<!-- CAL:%s:END -->)" % (name, name), re.S)
        if not global_s.search(s_holder[0]):
            sys.exit("Marker CAL:%s not found in page" % name)
        s_holder[0] = global_s.sub(lambda mt: mt.group(1) + "\n" + content + "\n" + mt.group(3), s_holder[0], count=1)
    s_holder = [s]
    put("MONTHS", mopts)
    put("TABLES", "\n".join(secs))
    lu = dt.date.fromisoformat(data["last_updated"])
    put("UPDATED", "Last updated %s." % human(lu))
    s = s_holder[0]
    s = re.sub(r'"dateModified":"\d{4}-\d{2}-\d{2}"', '"dateModified":"%s"' % lu.isoformat(), s, count=1)
    open(PAGE, "w", encoding="utf-8", newline="").write(s)
    print("Calendar rebuilt: %d rows across %d months, last updated %s" % (len(rows), len(months), lu.isoformat()))

if __name__ == "__main__":
    main()
