"""Rebuild the compliance calendar tables from tools/calendar.json.

Usage (from the repository root):  python tools/update_calendar.py
Rewrites the parts of compliance-calendar/index.html between the
CAL markers: the month dropdown, the month tables, and the 'Last updated' date,
and writes compliance-calendar/due-dates.ics, the subscribable calendar feed.
Standard library only.
"""
import json, os, re, sys, hashlib, datetime as dt
from html import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "compliance-calendar", "index.html")
DATA = os.path.join(ROOT, "tools", "calendar.json")
ICS = os.path.join(ROOT, "compliance-calendar", "due-dates.ics")
PAGE_URL = "https://vazassociates.in/compliance-calendar/"

def ics_text(t):
    return t.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

def ics_fold(line):
    b = line.encode("utf-8")
    if len(b) <= 75:
        return line
    out, cur = [], b""
    for ch in line:
        e = ch.encode("utf-8")
        if len(cur) + len(e) > (75 if not out else 74):
            out.append(cur.decode("utf-8")); cur = b""
        cur += e
    out.append(cur.decode("utf-8"))
    return "\r\n ".join(out)

def write_ics(rows, acts, lu):
    stamp = lu.strftime("%Y%m%dT000000Z")
    L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Vaz & Associates//Compliance calendar//EN",
         "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
         "X-WR-CALNAME:Compliance due dates (India) - vazassociates.in",
         "X-WR-CALDESC:" + ics_text("Statutory due dates under the Income-tax Act, GST, Companies Act, LLP Act, EPF and ESI and Maharashtra professional tax. Source: " + PAGE_URL),
         "X-WR-TIMEZONE:Asia/Kolkata", "REFRESH-INTERVAL;VALUE=DURATION:PT12H", "X-PUBLISHED-TTL:PT12H"]
    for d, r in rows:
        uid = hashlib.sha1((d.isoformat() + r["act"] + r["text"]).encode("utf-8")).hexdigest()[:20] + "@vazassociates.in"
        desc = "%s. Applies to: %s." % (acts[r["act"]], r.get("who", "")) if r.get("who") else acts[r["act"]] + "."
        if r.get("note"):
            desc += " " + r["note"].rstrip(".") + "."
        desc += " Check the current position before filing: " + PAGE_URL
        L += ["BEGIN:VEVENT", "UID:" + uid, "DTSTAMP:" + stamp,
              "DTSTART;VALUE=DATE:" + d.strftime("%Y%m%d"),
              "DTEND;VALUE=DATE:" + (d + dt.timedelta(days=1)).strftime("%Y%m%d"),
              "SUMMARY:" + ics_text("Due: " + r["text"]),
              "DESCRIPTION:" + ics_text(desc), "URL:" + PAGE_URL,
              "CATEGORIES:" + ics_text(acts[r["act"]]), "TRANSP:TRANSPARENT",
              "BEGIN:VALARM", "ACTION:DISPLAY", "DESCRIPTION:" + ics_text("Due: " + r["text"]),
              "TRIGGER:-P2D", "END:VALARM", "END:VEVENT"]
    L.append("END:VCALENDAR")
    open(ICS, "w", encoding="utf-8", newline="").write("\r\n".join(ics_fold(x) for x in L) + "\r\n")

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
    write_ics(rows, acts, lu)
    print("Calendar rebuilt: %d rows across %d months, last updated %s" % (len(rows), len(months), lu.isoformat()))

if __name__ == "__main__":
    main()
