"""Bring Ryan's Instagram reels onto the site, using the official Instagram API.

Usage (from the repository root, with INSTAGRAM_TOKEN set):
  python tools/update_reels.py home              latest 3 reels for the home page (assets/data/reels.json)
  python tools/update_reels.py captions BODY.md  add new captions to assets/data/reel_answers.json for review
  python tools/update_reels.py refresh           print a renewed token (tokens last 60 days)

Run by .github/workflows/instagram-reels.yml. The home page list is published directly. Captions
reach Piju only after Ryan merges the weekly pull request, because Piju repeats them word for word.
Without a token the script changes nothing and exits normally. Standard library only.
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME_FILE = ROOT / "assets" / "data" / "reels.json"
ANSWERS_FILE = ROOT / "assets" / "data" / "reel_answers.json"
API = "https://graph.instagram.com"
VERSION = "v26.0"
IST = timezone(timedelta(hours=5, minutes=30))
HOME_README = ("Written daily by tools/update_reels.py: the 3 newest Instagram reels shown on the home page. "
               "An empty list shows only the Follow panel.")
ANSWERS_README = ("Reel captions Piju may repeat, added by tools/update_reels.py through a weekly pull request. "
                  "To keep a reel out of Piju, set \"hide\": true on it; do not delete it, or it will be proposed again.")
MAX_CAPTION = 600
# Lines that ask for something rather than explain something, so Piju should not repeat them.
CTA = re.compile(r"\b(follow|dm|comment|like|share|save this|subscribe|link in bio|tag a|whatsapp|call us|contact us)\b", re.I)
# Wording to check against the ICAI guidelines. A flag only draws attention; it blocks nothing.
FLAGS = re.compile(r"\b(best|leading|top|no\.? ?1|number one|expert|guarantee\w*|cheapest|lowest|fees?|charges?|"
                   r"rs\.?|inr|discount|offer|free|testimonial|review|clients?)\b|₹", re.I)


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "vazassociates-site"}), timeout=60) as r:
        return json.load(r)


def fetch_reels(token):
    """All reels on the account, newest first."""
    query = urllib.parse.urlencode({"fields": "id,caption,media_product_type,permalink,timestamp",
                                    "limit": 50, "access_token": token})
    url, reels = f"{API}/{VERSION}/me/media?{query}", []
    for _ in range(100):
        page = get_json(url)
        reels += [m for m in page.get("data", []) if m.get("media_product_type") == "REELS" and m.get("permalink")]
        url = page.get("paging", {}).get("next")
        if not url:
            break
    return sorted(reels, key=lambda m: when(m), reverse=True)


def when(reel):
    return datetime.strptime(reel["timestamp"], "%Y-%m-%dT%H:%M:%S%z").astimezone(IST)


def clean_caption(text):
    """The explanatory part of a caption: no hashtags, mentions, links or calls to action."""
    keep = []
    for line in (text or "").splitlines():
        line = re.sub(r"https?://\S+|\b\S+\.in\b|[#@][\w.]+", "", line)
        line = re.sub(r"\s+", " ", line).strip(" -|•·")
        if line and not CTA.search(line):
            keep.append(line)
    out = " ".join(keep)
    if len(out) > MAX_CAPTION:
        out = out[:MAX_CAPTION].rsplit(" ", 1)[0] + " ..."
    return out


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def update_home(reels):
    """Returns True if the home page list changed."""
    if not reels:
        print("The API returned no reels; home page list left as it is.")
        return False
    new = {"_readme": HOME_README,
           "reels": [{"url": r["permalink"], "date": when(r).date().isoformat()} for r in reels[:3]]}
    old = json.loads(HOME_FILE.read_text(encoding="utf8")) if HOME_FILE.exists() else {}
    if old.get("reels") == new["reels"]:
        print("Home page reels unchanged.")
        return False
    write_json(HOME_FILE, new)
    print("Home page reels updated.")
    return True


def update_captions(reels, body_path):
    """Adds new reels, drops reels removed from Instagram, leaves reviewed entries alone. Returns the number added."""
    data = {"_readme": ANSWERS_README, "reels": []}
    if ANSWERS_FILE.exists():
        data["reels"] = json.loads(ANSWERS_FILE.read_text(encoding="utf8")).get("reels", [])
    if not reels:
        print("The API returned no reels; captions left as they are.")
        return 0
    live = {r["id"] for r in reels}
    kept = [e for e in data["reels"] if e["id"] in live]
    removed = len(data["reels"]) - len(kept)
    known = {e["id"] for e in kept}
    added = []
    for r in reels:
        if r["id"] in known:
            continue
        added.append({"id": r["id"], "url": r["permalink"], "date": when(r).date().isoformat(),
                      "caption": clean_caption(r.get("caption"))})
    data["reels"] = sorted(kept + added, key=lambda e: e["date"], reverse=True)
    if not added and not removed:
        print("No new reels.")
        return 0
    write_json(ANSWERS_FILE, data)
    lines = [f"New reel captions for Piju: {len(added)}. Reels no longer on Instagram, removed: {removed}.", "",
             "Piju repeats these word for word once merged. Check them against the ICAI guidelines and for law "
             "that may have changed. To keep one out, set \"hide\": true on it in reel_answers.json, or ask Claude to.", ""]
    for e in added:
        flags = sorted({m.group(0).lower() for m in FLAGS.finditer(e["caption"])})
        lines.append(f"- {e['date']}: {e['url']}")
        lines.append(f"  - {e['caption'] or '(no usable text; Piju will skip this reel)'}")
        if flags:
            lines.append(f"  - Wording to check: {', '.join(flags)}")
    Path(body_path).write_text("\n".join(lines) + "\n", encoding="utf8")
    print(f"{len(added)} captions added, {removed} removed.")
    return len(added) + removed


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in ("home", "captions", "refresh"):
        raise SystemExit(__doc__)
    token = os.environ.get("INSTAGRAM_TOKEN", "").strip()
    if not token:
        print("INSTAGRAM_TOKEN is not set yet; nothing changed.", file=sys.stderr)
        return
    if mode == "refresh":
        query = urllib.parse.urlencode({"grant_type": "ig_refresh_token", "access_token": token})
        print(get_json(f"{API}/refresh_access_token?{query}")["access_token"])
    elif mode == "home":
        update_home(fetch_reels(token))
    else:
        update_captions(fetch_reels(token), sys.argv[2])


if __name__ == "__main__":
    main()
