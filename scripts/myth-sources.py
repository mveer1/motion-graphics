#!/usr/bin/env python3
"""
scripts/myth-sources.py - find public-domain artworks of myths, gods and heroes for photo plates.

Searches museum open-access APIs that need no key and returns only images that are public
domain or CC0, as records the collage fetcher downloads politely and validates:

    python scripts/myth-sources.py search "Krishna Govardhan" --source cma,met,commons --limit 12 \
        --out projects/<slug>/research/plates.json
    python .claude/skills/collage-design/scripts/fetch.py --json projects/<slug>/research/plates.json \
        --out projects/<slug>/assets/plates --attributions projects/<slug>/research/plate-credits.md
    python scripts/assets.py import <slug> projects/<slug>/assets/plates/<file> --license-status verified

Sources (checked live 2026-11-23, see .claude/skills/mythic-tales/references/imagery-sourcing.md):
  cma      Cleveland Museum of Art open access: `cc0` filter, culture and creators included.
  met      The Met collection API: v1.1 search (v1 retired 2026-10-01) returns ids only; each
           object is fetched and kept only when isPublicDomain is true and it has an image.
  commons  Wikimedia Commons: file search plus extmetadata; kept only when LicenseShortName is
           public domain or CC0 (CC BY-SA and the like are dropped).
Not wired: the Art Institute of Chicago (Cloudflare blocks scripts), Smithsonian (needs a key),
Openverse (200 anonymous requests a day). Records carry the licence the museum states; a person
still checks each image (iconography, subject, the museum's page) before it is used.

Politeness: one request at a time, a pause between calls, and a descriptive User-Agent (set
MOTIONLAB_CONTACT to an e-mail or URL; Wikimedia's policy asks for one). Stdlib only.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, List, Optional

CONTACT = os.environ.get("MOTIONLAB_CONTACT", "https://github.com/mveer1/motion-graphics")
UA = f"MotionLab-myth-sources/0.1 ({CONTACT}) python-urllib/{sys.version_info.major}.{sys.version_info.minor}"
PAUSE_SEC = 0.6
MET = "https://collectionapi.metmuseum.org/public/collection"
CMA = "https://openaccess-api.clevelandart.org/api/artworks/"
COMMONS = "https://commons.wikimedia.org/w/api.php"
PD_LICENCES = re.compile(r"^(public domain|pd\b|pd-|cc0|cc-zero|no restrictions)", re.I)
# Raster images only: Commons also serves scanned books (DjVu, PDF) under image/ MIME types.
IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/tiff"}

Record = Dict[str, Any]


def strip_tags(text: Any) -> str:
    text = re.sub(r"<div[^>]*display:\s*none[^>]*>.*?</div>", "", str(text or ""), flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text))).strip()


def attribution(rec: Record) -> str:
    who = rec.get("creator") or rec.get("culture") or "Unknown maker"
    parts = [rec.get("title") or "Untitled", who, rec.get("date") or ""]
    return ", ".join(p for p in parts if p) + f". {rec['institution']}. {rec['license']}."


def finish(rec: Record) -> Record:
    rec["attribution"] = attribution(rec)
    return rec


# ---------------------------------------------------------------- parsers (pure; tested offline)
def parse_cma(payload: Dict[str, Any]) -> List[Record]:
    out = []
    for a in payload.get("data", []):
        img = ((a.get("images") or {}).get("web") or {}).get("url")
        if not img or str(a.get("share_license_status", "")).upper() != "CC0":
            continue
        creators = "; ".join(strip_tags(c.get("description")) for c in a.get("creators") or [] if c.get("description"))
        out.append(finish({
            "url": img, "id": f"cma-{a.get('accession_number') or a.get('id')}", "title": strip_tags(a.get("title")),
            "creator": creators, "date": strip_tags(a.get("creation_date")), "culture": ", ".join(a.get("culture") or []),
            "license": "CC0", "source": a.get("url") or "", "institution": "The Cleveland Museum of Art",
        }))
    return out


def parse_met_object(obj: Dict[str, Any]) -> Optional[Record]:
    img = obj.get("primaryImageSmall") or obj.get("primaryImage")
    if not obj.get("isPublicDomain") or not img:
        return None
    culture = obj.get("culture") or obj.get("period") or ", ".join(x for x in (obj.get("region"), obj.get("country")) if x)
    return finish({
        "url": img, "id": f"met-{obj.get('objectID')}", "title": strip_tags(obj.get("title")),
        "creator": strip_tags(obj.get("artistDisplayName")), "date": strip_tags(obj.get("objectDate")),
        "culture": strip_tags(culture), "license": "Public domain (CC0, Met Open Access)",
        "source": obj.get("objectURL") or "", "institution": "The Metropolitan Museum of Art",
    })


def parse_commons(payload: Dict[str, Any]) -> List[Record]:
    out = []
    pages = (payload.get("query") or {}).get("pages") or []
    if isinstance(pages, dict):
        pages = list(pages.values())
    for page in sorted(pages, key=lambda p: p.get("index", 0)):
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        lic = strip_tags((meta.get("LicenseShortName") or {}).get("value"))
        if not lic or not PD_LICENCES.match(lic) or str(info.get("mime", "image/jpeg")).lower() not in IMAGE_MIMES:
            continue
        title = strip_tags((meta.get("ObjectName") or {}).get("value")) or re.sub(r"^File:|\.[a-z0-9]+$", "", page.get("title", ""), flags=re.I)
        out.append(finish({
            "url": info.get("thumburl") or info.get("url"), "id": f"commons-{page.get('pageid')}", "title": title,
            "creator": strip_tags((meta.get("Artist") or {}).get("value")),
            "date": strip_tags((meta.get("DateTimeOriginal") or {}).get("value")), "culture": "",
            "license": lic, "source": info.get("descriptionurl") or "", "institution": "Wikimedia Commons",
        }))
    return out


# ---------------------------------------------------------------- network
def get_json(url: str, tries: int = 4) -> Any:
    delay = 1.0
    for attempt in range(1, tries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                data = json.loads(r.read().decode("utf-8"))
            time.sleep(PAUSE_SEC)
            return data
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < tries:
                time.sleep(float(e.headers.get("Retry-After") or 0) or delay)
                delay = min(delay * 2, 30)
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            if attempt < tries:
                time.sleep(delay)
                delay = min(delay * 2, 30)
                continue
            raise
    raise RuntimeError(f"gave up: {url}")


def search_cma(q: str, limit: int, fetch: Callable[[str], Any] = get_json) -> List[Record]:
    fields = "id,accession_number,title,creation_date,culture,creators,url,images,share_license_status"
    url = CMA + "?" + urllib.parse.urlencode({"q": q, "has_image": 1, "limit": limit, "fields": fields}) + "&cc0"
    return parse_cma(fetch(url))[:limit]


def search_met(q: str, limit: int, fetch: Callable[[str], Any] = get_json) -> List[Record]:
    query = urllib.parse.urlencode({"q": q, "hasImages": "true", "limit": max(limit * 4, 20)})
    try:
        ids = (fetch(f"{MET}/v1.1/search?{query}") or {}).get("objectIDs") or []
    except urllib.error.HTTPError as e:
        if e.code not in (404, 410):
            raise
        ids = (fetch(f"{MET}/v1/search?{query}") or {}).get("objectIDs") or []
    out: List[Record] = []
    for oid in ids[: max(limit * 8, 40)]:
        try:
            obj = fetch(f"{MET}/v1/objects/{oid}") or {}
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):   # the search index lists objects that no longer resolve
                continue
            raise
        rec = parse_met_object(obj)
        if rec:
            out.append(rec)
        if len(out) >= limit:
            break
    return out


def search_commons(q: str, limit: int, fetch: Callable[[str], Any] = get_json) -> List[Record]:
    params = {
        "action": "query", "generator": "search", "gsrsearch": q, "gsrnamespace": 6, "gsrlimit": max(limit * 3, 10),
        "prop": "imageinfo", "iiprop": "url|extmetadata|mime|size", "iiurlwidth": 1600, "format": "json", "formatversion": 2,
        "iiextmetadatafilter": "LicenseShortName|Artist|ObjectName|DateTimeOriginal|Restrictions|AttributionRequired",
    }
    return parse_commons(fetch(COMMONS + "?" + urllib.parse.urlencode(params)))[:limit]


SOURCES = {"cma": search_cma, "met": search_met, "commons": search_commons}


def cmd_search(a: argparse.Namespace) -> int:
    records: List[Record] = []
    for src in [s.strip() for s in a.source.split(",") if s.strip()]:
        if src not in SOURCES:
            raise SystemExit(f"unknown source '{src}' (use {', '.join(SOURCES)})")
        try:
            found = SOURCES[src](a.query, a.limit)
        except Exception as exc:  # one archive down must not lose the others
            print(f"[{src}] failed: {exc}", file=sys.stderr)
            continue
        print(f"[{src}] {len(found)} public-domain image(s)", file=sys.stderr)
        records += found
    if a.culture:
        rx = re.compile(a.culture, re.I)
        records = [r for r in records if rx.search(" ".join([r["culture"], r["title"], r["creator"]]))]
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(records, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        print(f"wrote {len(records)} record(s) to {a.out}", file=sys.stderr)
    if a.json:
        print(json.dumps(records, indent=2, ensure_ascii=False))
    else:
        for r in records:
            print(f"{r['id']:<22} {r['title'][:52]:<52} | {(r['culture'] or r['creator'])[:30]:<30} | {r['license'][:16]:<16} | {r['source']}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Find public-domain artworks of myths for photo plates.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search", help="search museum open-access APIs")
    s.add_argument("query")
    s.add_argument("--source", default="cma,met,commons", help="comma list of cma, met, commons")
    s.add_argument("--limit", type=int, default=8, help="images per source")
    s.add_argument("--culture", help="regex kept against culture, title and maker (e.g. 'India|Nepal')")
    s.add_argument("--out", help="write records for .claude/skills/collage-design/scripts/fetch.py --json")
    s.add_argument("--json", action="store_true", help="print records as JSON")
    s.set_defaults(fn=cmd_search)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
