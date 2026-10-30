#!/usr/bin/env python3
"""
sfx-openverse.py
CLI tool to search, query, and download openly-licensed sound effects and audio clips
from Openverse (Creative Commons) for the Motion Graphics production pipeline.

Usage:
  python3 scripts/sfx-openverse.py "mechanical click" --limit 3
  python3 scripts/sfx-openverse.py "whoosh transition" --limit 5 --download --out-dir assets/audio/sfx
  python3 scripts/sfx-openverse.py "subtle chime" --license cc0 --download --out-dir projects/my-proj/audio/sfx
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path


OPENVERSE_AUDIO_API = "https://api.openverse.org/v1/audio/"


def search_openverse(query: str, page_size: int = 5, license_filter: str = "cc0,by", retries: int = 2):
    params = {
        "q": query,
        "page_size": page_size,
    }
    if license_filter:
        params["license"] = license_filter

    url = f"{OPENVERSE_AUDIO_API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "AntigravityMotionGraphics/1.0 (audio-pipeline)"}
    )

    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("results", [])
        except Exception as e:
            if attempt == retries:
                print(f"Error fetching from Openverse API after {retries + 1} attempts: {e}", file=sys.stderr)
            continue
    return []


def download_audio_file(url: str, dest_path: Path) -> bool:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "AntigravityMotionGraphics/1.0 (audio-pipeline)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp, open(dest_path, "wb") as f:
            f.write(resp.read())
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="Search and download Openverse audio assets.")
    parser.add_argument("query", help="Search query (e.g., 'whoosh', 'camera shutter', 'pop')")
    parser.add_argument("-n", "--limit", type=int, default=5, help="Number of results (default: 5)")
    parser.add_argument("--license", default="cc0,by", help="Comma-separated license filters (e.g., 'cc0,by')")
    parser.add_argument("--download", action="store_true", help="Download audio files to --out-dir")
    parser.add_argument("--out-dir", default="assets/audio/sfx", help="Output directory for downloaded files")
    parser.add_argument("--json", action="store_true", help="Output results strictly as JSON")

    args = parser.parse_args()

    results = search_openverse(args.query, page_size=args.limit, license_filter=args.license)

    output_items = []
    out_dir = Path(args.out_dir).resolve()

    for item in results:
        audio_id = item.get("id")
        title = item.get("title", "untitled")
        creator = item.get("creator", "unknown")
        license_code = item.get("license", "unknown")
        attribution = item.get("attribution", "")
        duration_ms = item.get("duration", 0)
        provider = item.get("provider", "openverse")
        filetype = item.get("filetype", "mp3")

        # Choose download URL: Openverse provides high-quality public preview audio in item["url"]
        download_url = item.get("url")
        filetype = item.get("filetype", "mp3")

        local_path = None
        if args.download and download_url:
            safe_slug = "".join(c if c.isalnum() or c in "-_" else "_" for c in f"{provider}_{title[:30]}_{audio_id[:8]}")
            dest_file = out_dir / f"{safe_slug}.{filetype}"
            success = download_audio_file(download_url, dest_file)
            if success:
                local_path = str(dest_file)

        output_items.append({
            "id": audio_id,
            "title": title,
            "creator": creator,
            "license": license_code,
            "duration_ms": duration_ms,
            "duration_sec": round(duration_ms / 1000.0, 3) if duration_ms else None,
            "provider": provider,
            "attribution": attribution,
            "remote_url": download_url,
            "local_path": local_path,
            "tags": [t.get("name") for t in item.get("tags", []) if isinstance(t, dict)]
        })

    if args.json:
        print(json.dumps(output_items, indent=2))
        return

    # Readable formatted report
    print(f"\n--- Openverse Audio Search: '{args.query}' ({len(output_items)} results) ---")
    for i, item in enumerate(output_items, start=1):
        dur = f"{item['duration_sec']}s" if item['duration_sec'] else "unknown duration"
        print(f"[{i}] {item['title']} ({dur})")
        print(f"    Creator: {item['creator']} | License: {item['license']} | Provider: {item['provider']}")
        print(f"    Attribution: {item['attribution']}")
        if item.get("local_path"):
            print(f"    Downloaded: {item['local_path']}")
        else:
            print(f"    Audio URL: {item['remote_url']}")
        print()


if __name__ == "__main__":
    main()
