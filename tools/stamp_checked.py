"""Stamp today's date (IST) as the date of the latest successful compliance check.

Run by the Daily compliance check workflow only when every source was checked and nothing needed
changing. It moves the visible "Status as on" / "Last updated" dates on the News, Compliance calendar,
GST updates and the FAQ "GST changes" section, and the matching sitemap lastmod values. It does not
change last_updated in news.json or calendar.json (that stays the date of the last real change);
it sets last_checked instead.

Usage: python3 tools/stamp_checked.py [YYYY-MM-DD]
"""
import json, re, subprocess, sys, datetime as dt

ROOT = __file__.replace("\\", "/").rsplit("/tools/", 1)[0]
today = dt.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else \
    (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=5, minutes=30)).date()
human = "%d %s %d" % (today.day, today.strftime("%B"), today.year)

def rw(path, fn):
    p = ROOT + "/" + path
    s = open(p, encoding="utf-8").read()
    t = fn(s)
    if t != s:
        open(p, "w", encoding="utf-8", newline="\n").write(t)

for j in ("tools/news.json", "tools/calendar.json"):
    rw(j, lambda s: re.sub(r'("last_checked":\s*")[0-9-]+(")', r"\g<1>%s\2" % today.isoformat(), s)
       if '"last_checked"' in s else
       re.sub(r'("last_updated":\s*"[0-9-]+",)', r'\1\n  "last_checked": "%s",' % today.isoformat(), s, count=1))

subprocess.check_call([sys.executable, ROOT + "/tools/update_news.py"])
subprocess.check_call([sys.executable, ROOT + "/tools/update_calendar.py"])

status = re.compile(r"Status as on [0-9]{1,2} [A-Z][a-z]+ [0-9]{4}\.")
rw("services/gst-updates/index.html", lambda s: status.sub("Status as on %s." % human, s, count=1))

def faq(s):  # only the "GST changes 2026-27" group (id g6)
    return re.sub(r'(<h2 id="g6">.*?<p class="muted">)Status as on [0-9]{1,2} [A-Z][a-z]+ [0-9]{4}\.',
                  r"\g<1>Status as on %s." % human, s, count=1, flags=re.S)
rw("faq/index.html", faq)

def sitemap(s):
    for path in ("news/", "compliance-calendar/", "services/gst-updates/", "faq/"):
        s = re.sub(r"(<loc>https://vazassociates\.in/%s</loc>\s*<lastmod>)[0-9-]+" % re.escape(path),
                   r"\g<1>%s" % today.isoformat(), s)
    return s
rw("sitemap.xml", sitemap)
print("Stamped checked on", human)
