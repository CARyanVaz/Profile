"""Send the pages changed between two commits to IndexNow (Bing, Yandex, Seznam, Naver).

Usage:  python tools/indexnow.py <old-commit> <new-commit>
Uses the key file already at the site root (b0128229e651a5993269d30c135e7e0a.txt).
Google does not use IndexNow; Google reads sitemap.xml.
Standard library only.
"""
import json, os, re, subprocess, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = "vazassociates.in"
KEY = "b0128229e651a5993269d30c135e7e0a"


def changed_pages(old, new):
    try:
        if not old or set(old) == {"0"}:
            raise ValueError
        out = subprocess.check_output(["git", "diff", "--name-only", "--diff-filter=AM", old, new], cwd=ROOT, text=True)
    except Exception:
        out = subprocess.check_output(["git", "show", "--name-only", "--pretty=", new], cwd=ROOT, text=True)
    urls = []
    for f in out.split():
        if not f.endswith(".html") or re.match(r"(google[0-9a-f]+|404)\.html$", os.path.basename(f)) or not os.path.isfile(os.path.join(ROOT, f)):
            continue
        if re.search(r'<meta[^>]+name="robots"[^>]+noindex', open(os.path.join(ROOT, f), encoding="utf-8").read()):
            continue
        path = "/" if f == "index.html" else "/" + (f[:-10] if f.endswith("/index.html") else f)
        urls.append(f"https://{HOST}{path}")
    return sorted(set(urls))


def main():
    old = sys.argv[1] if len(sys.argv) > 1 else ""
    new = sys.argv[2] if len(sys.argv) > 2 else "HEAD"
    urls = changed_pages(old, new)
    if not urls:
        print("No changed pages to send.")
        return
    body = json.dumps({"host": HOST, "key": KEY, "keyLocation": f"https://{HOST}/{KEY}.txt", "urlList": urls[:10000]}).encode()
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body, headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"IndexNow answered {r.status} for {len(urls)} pages:")
    except urllib.error.HTTPError as e:
        print(f"IndexNow answered {e.code}: {e.read().decode()[:300]}")
        sys.exit(0 if e.code in (200, 202) else 1)
    print("\n".join(urls))


if __name__ == "__main__":
    main()
