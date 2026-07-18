#!/usr/bin/env python3
"""
Convert a JioTV-style .m3u playlist (with #KODIPROP clearkey lines and a
Cookie query param appended to the stream URL) into a JSON file.

Usage:
    python3 m3u_to_json.py [source] [-o output.json]

    source can be:
        - a local file path to the .m3u file, or
        - an http(s) URL (it will be downloaded first)

    If source is omitted, it defaults to the raw GitHub URL used below.

Each entry in the output JSON looks like:
{
    "id": "143",
    "name": "CNBC TV18 Prime",
    "stream_url": "https://jiotvmblive.cdn.jio.com/bpk-tv/CNBCTV18Prime_MOB/WDVLive/index.mpd",
    "cookie": "__hdnea__=st=1784384983~exp=1784406583~acl=/*~hmac=...",
    "cookie_expires": "19/7/2026 6:00:27 AM IST",
    "key_id": "eb19113c11ce5cfb80c89696765a0187",
    "key": "b2797ce5e403ee22d8e36c6d5f2b6630"
}
"""

import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

DEFAULT_SOURCE = "https://raw.githubusercontent.com/sixpg/zeyo/refs/heads/main/jtv.m3u"
IST = timezone(timedelta(hours=5, minutes=30))


def fetch_source(source: str) -> str:
    """Return the raw text of the m3u playlist, whether source is a URL or a local path."""
    if source.startswith("http://") or source.startswith("https://"):
        req = urllib.request.Request(source, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    with open(source, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def format_expiry(exp_ts: str) -> str:
    """Convert a unix timestamp string to a 'D/M/YYYY H:MM:SS AM/PM IST' string."""
    try:
        dt = datetime.fromtimestamp(int(exp_ts), tz=IST)
    except (ValueError, OSError):
        return ""
    hour12 = dt.hour % 12
    if hour12 == 0:
        hour12 = 12
    ampm = "AM" if dt.hour < 12 else "PM"
    return f"{dt.day}/{dt.month}/{dt.year} {hour12}:{dt.minute:02d}:{dt.second:02d} {ampm} IST"


def parse_m3u(text: str):
    """Parse the m3u content and yield channel dicts."""
    lines = [l.rstrip("\n") for l in text.split("\n")]

    channels = []
    current = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("#EXTINF"):
            # Start a new channel entry
            current = {}
            tvg_id_match = re.search(r'tvg-id="([^"]*)"', line)
            name_match = re.search(r",(.*)$", line)
            current["id"] = tvg_id_match.group(1) if tvg_id_match else ""
            current["name"] = name_match.group(1).strip() if name_match else ""
            current["key_id"] = None
            current["key"] = None

        elif line.startswith("#KODIPROP:inputstream.adaptive.license_key="):
            if current is not None:
                key_val = line.split("=", 1)[1]
                if ":" in key_val:
                    key_id, key = key_val.split(":", 1)
                    current["key_id"] = key_id
                    current["key"] = key

        elif line.startswith("#") :
            # other metadata lines (KODIPROP license_type, EXTM3U, etc.) - ignore
            continue

        else:
            # This should be the stream URL line, optionally with |Cookie=...
            if current is None:
                continue

            if "|" in line:
                url_part, cookie_part = line.split("|", 1)
            else:
                url_part, cookie_part = line, ""

            stream_url = url_part.strip()
            cookie = ""
            if cookie_part:
                # cookie_part looks like: Cookie=__hdnea__=st=...~exp=...~acl=...~hmac=...
                cookie = cookie_part.strip()
                if cookie.lower().startswith("cookie="):
                    cookie = cookie.split("=", 1)[1]

            current["stream_url"] = stream_url
            current["cookie"] = cookie

            # Extract expiry timestamp from the cookie string (exp=...)
            exp_match = re.search(r"exp=(\d+)", cookie)
            current["cookie_expires"] = format_expiry(exp_match.group(1)) if exp_match else ""

            channels.append(current)
            current = None

    return channels


def main():
    parser = argparse.ArgumentParser(description="Convert JioTV .m3u playlist to JSON")
    parser.add_argument("source", nargs="?", default=DEFAULT_SOURCE,
                         help="Path or URL to the .m3u file (default: the sixpg/zeyo jtv.m3u on GitHub)")
    parser.add_argument("-o", "--output", default="jtv.json",
                         help="Output JSON file path (default: jtv.json)")
    args = parser.parse_args()

    print(f"Fetching playlist from: {args.source}")
    text = fetch_source(args.source)

    channels = parse_m3u(text)
    print(f"Parsed {len(channels)} channels.")

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(channels, f, indent=4, ensure_ascii=False)

    print(f"Saved JSON to: {args.output}")


if __name__ == "__main__":
    main()
